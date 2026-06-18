# Social production readiness — one-shot (read-only)

**GM preference:** Option A — no file writes on prod app tree, no restart.  
**Use when:** readiness script not yet on prod HEAD (before PR #48 merge).

---

## Owner run (recommended — paste-safe)

One block: writes script to `/tmp`, runs read-only probe. **Does not modify `/var/www/mywave/.env`.**

```bash
PROD_ROOT=/var/www/mywave
cat >/tmp/prod_social_readiness_oneshot.py <<'PYEOF'
#!/usr/bin/env python3
import os, re, sys
from pathlib import Path

def tail(v, n=8):
    v = (v or "").strip().strip('"').strip("'")
    return v[-n:] if len(v) >= n else v

def lines(p):
    return p.read_text(encoding="utf-8", errors="replace").splitlines() if p.is_file() else []

def vals(lines, key):
    out = []
    for ln in lines:
        if ln.strip().startswith("#"): continue
        m = re.match(rf"^{re.escape(key)}=(.*)$", ln.strip())
        if m: out.append(m.group(1).strip())
    return out

prod = Path(os.environ.get("PROD_ROOT", "/var/www/mywave"))
env = prod / ".env"
L = lines(env)
print("=== Social readiness one-shot (read-only) ===")
print("root=", prod)
sp = [(i+1, m.group(1).strip()) for i, ln in enumerate(L) if (m := re.match(r"^SPREADSHEET_ID=(.*)$", ln.strip()))]
print("\n=== SPREADSHEET_ID duplicate check ===")
print("SPREADSHEET_ID line count:", len(sp), "(expect 1)")
for n, v in sp: print(f"{n}:SPREADSHEET_ID=***{tail(v)}")
if len(sp) == 1 and tail(sp[0][1]) == "akVMOrCgic0": print("OK: single Admin SPREADSHEET_ID")
elif len(sp) > 1: print("FAIL: dedupe .env — remove Parser line from SPREADSHEET_ID; use PARSER_NEWS_SPREADSHEET_ID")
pv = vals(L, "PARSER_NEWS_SPREADSHEET_ID")
print("\n=== PARSER_NEWS tail ===")
if pv:
    print(f"PARSER_NEWS_SPREADSHEET_ID=***{tail(pv[-1])}")
    print("OK: Parser tail" if tail(pv[-1]) == "LijNNyn50" else "FAIL/WARN: expected LijNNyn50")
else: print("FAIL: PARSER_NEWS_SPREADSHEET_ID not set")
sv = vals(L, "SOCIAL_SPREADSHEET_ID")
sid = sv[-1] if sv and sv[-1] else (sp[-1][1] if sp else "")
print("\n=== SOCIAL effective tail ===")
print("SOCIAL_SPREADSHEET_ID:", "set" if sv and sv[-1] else "empty → fallback last SPREADSHEET_ID")
print("effective_social_tail: ***" + tail(sid))
if tail(sid) == "akVMOrCgic0": print("OK: Admin for Social")
elif tail(sid) == "LijNNyn50": print("FAIL: Social on Parser sheet")
tab = (vals(L, "SOCIAL_APPLICATIONS_SHEET_NAME") or ["Social_Applications"])[-1]
print("\n=== Google SA + tab probe ===")
sys.path.insert(0, str(prod)); os.chdir(prod)
from app import create_app
app = create_app("production")
with app.app_context():
    from app.services.google import get_google_services
    _, sheets, _ = get_google_services()
    meta = sheets.spreadsheets().get(spreadsheetId=sid.strip().strip('"')).execute()
    titles = [s["properties"]["title"] for s in meta.get("sheets", [])]
    print("probe_tail", tail(sid))
    print("spreadsheet_access=OK")
    print("tabs_count", len(titles))
    print("Social_Applications_tab", "YES" if tab in titles else "NO")
print("\n=== DONE ===")
PYEOF
PROD_ROOT=/var/www/mywave "${PROD_ROOT}/venv/bin/python" /tmp/prod_social_readiness_oneshot.py
```

After PR #48 on prod, same logic lives in `scripts/prod_social_readiness_oneshot.py`.

---

## Interpret Owner output (2026-06-18 partial run)

| Check | Result |
|-------|--------|
| `SPREADSHEET_ID` count | **FAIL: 2 lines** (L31 Parser prefix `1RJpw2mA`, L36 Admin `1kyNQVje`) |
| Social fallback (last line) | **OK** tail `MOrCgic0` (= `akVMOrCgic0`) |
| `PARSER_NEWS` | **Inconclusive** (paste corrupted) — re-run |
| SA / `Social_Applications` | **Inconclusive** — Flask app context error in old one-liner; fixed above |
| `.env` dedupe | **Required before rollout** — see below |

**Runtime note:** `load_dotenv()` last key wins → effective `SPREADSHEET_ID` likely Admin (L36), but duplicate L31 is **FAIL** for readiness and risky.

---

## .env fix (Owner manual — no commit)

Keep **one** Admin line on `SPREADSHEET_ID`; move Parser to dedicated key only:

```env
# REMOVE duplicate — do not use SPREADSHEET_ID for Parser
PARSER_NEWS_SPREADSHEET_ID=<full_id tail LijNNyn50>
SPREADSHEET_ID=<full_id tail akVMOrCgic0>
# optional before Social flags:
SOCIAL_SPREADSHEET_ID=<same Admin id>
```

Verify tails:

```bash
grep -n '^SPREADSHEET_ID=\|^PARSER_NEWS_SPREADSHEET_ID=' /var/www/mywave/.env | sed -E 's/=.*(.{8})$/=***\1/'
```

Expect: **one** `SPREADSHEET_ID=***OrCgic0`, `PARSER_NEWS=***NNyn50`.

Restart **not** required for readiness probe; restart **required** after `.env` dedupe before Social flags ON.

---

## Option B — scp from repo

```bash
scp scripts/prod_social_readiness_oneshot.py user@prod:/tmp/
ssh user@prod 'PROD_ROOT=/var/www/mywave /var/www/mywave/venv/bin/python /tmp/prod_social_readiness_oneshot.py'
```

---

## PASS criteria

| Check | Expected |
|-------|----------|
| `SPREADSHEET_ID` lines | 1, tail `akVMOrCgic0` |
| `PARSER_NEWS_SPREADSHEET_ID` tail | `LijNNyn50` |
| Social effective tail | `akVMOrCgic0` |
| `spreadsheet_access` | OK |
| `Social_Applications_tab` | YES |

---

## Does not

- Write prod `.env` (Owner dedupe is separate manual step)
- Restart `mywave-site`
- Mutate Sheets
- Enable Social flags
