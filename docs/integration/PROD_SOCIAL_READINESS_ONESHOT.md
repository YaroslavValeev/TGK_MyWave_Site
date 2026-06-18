# Social production readiness — one-shot (read-only)

**GM preference:** Option A — no file writes on prod, no restart, no app code deploy.  
**Use when:** `prod_social_readiness_check.sh` is not yet on prod HEAD (before PR #48 merge).

---

## Option A — paste on prod server

```bash
PROD_ROOT=/var/www/mywave
set -euo pipefail

echo "=== Social readiness one-shot (read-only) ==="
echo "root=${PROD_ROOT}"

echo ""
echo "=== SPREADSHEET_ID duplicate check ==="
SP_COUNT=$(grep -cE '^SPREADSHEET_ID=' "${PROD_ROOT}/.env" 2>/dev/null || echo 0)
echo "SPREADSHEET_ID line count: ${SP_COUNT}"
[ "${SP_COUNT}" -eq 1 ] && echo "OK: single SPREADSHEET_ID" || echo "FAIL/WARN: expected 1 line"
grep -nE '^SPREADSHEET_ID=' "${PROD_ROOT}/.env" | sed -E 's/=(.{8}).*/=***\1/'

echo ""
echo "=== PARSER_NEWS tail (blog isolation) ==="
grep -E '^PARSER_NEWS_SPREADSHEET_ID=' "${PROD_ROOT}/.env" | sed -E 's/=(.{8}).*/=***\1/' \
  | grep -q 'NNyn50' && echo "OK: Parser tail NNyn50" || echo "FAIL/WARN: expected ***NNyn50"

echo ""
echo "=== SOCIAL effective spreadsheet tail ==="
SOCIAL_SID=$(grep -E '^SOCIAL_SPREADSHEET_ID=' "${PROD_ROOT}/.env" 2>/dev/null | cut -d= -f2- | tr -d '\r"' || true)
if [ -z "${SOCIAL_SID}" ]; then
  SOCIAL_SID=$(grep -E '^SPREADSHEET_ID=' "${PROD_ROOT}/.env" | tail -1 | cut -d= -f2- | tr -d '\r"')
  echo "SOCIAL_SPREADSHEET_ID: empty → fallback SPREADSHEET_ID (last line)"
else
  echo "SOCIAL_SPREADSHEET_ID: set"
fi
TAIL="${SOCIAL_SID: -8}"
echo "effective_social_tail: ***${TAIL}"
case "${TAIL}" in
  akVMOrCgic0) echo "OK: Admin table for Social" ;;
  LijNNyn50)   echo "FAIL: Social must not use Parser sheet" ;;
  *)           echo "WARN: unexpected tail — verify .env" ;;
esac

echo ""
echo "=== Google SA + Social_Applications tab (read-only API) ==="
"${PROD_ROOT}/venv/bin/python" - <<'PY'
import os, sys
PROD_ROOT = os.environ.get("PROD_ROOT", "/var/www/mywave")
sys.path.insert(0, PROD_ROOT)
os.chdir(PROD_ROOT)
from dotenv import load_dotenv
load_dotenv(f"{PROD_ROOT}/.env")
sid = (os.getenv("SOCIAL_SPREADSHEET_ID") or os.getenv("SPREADSHEET_ID") or "").strip()
tab = (os.getenv("SOCIAL_APPLICATIONS_SHEET_NAME") or "Social_Applications").strip()
if not sid:
    raise SystemExit("FAIL: no SPREADSHEET_ID / SOCIAL_SPREADSHEET_ID")
print("probe_tail", sid[-8:])
from app.services.google import get_google_services
meta = get_google_services()["sheets"].spreadsheets().get(spreadsheetId=sid).execute()
titles = [s["properties"]["title"] for s in meta.get("sheets", [])]
print("spreadsheet_access=OK")
print("tabs_count", len(titles))
print("Social_Applications_tab", "YES" if tab in titles else "NO")
PY

echo ""
echo "=== Booking/calendar isolation (static) ==="
echo "social.py not on prod HEAD yet — isolation confirmed in release branch code review (no booking/calendar imports)"

echo ""
echo "=== DONE — paste output to GM thread (tails only) ==="
```

**PASS criteria:**

| Check | Expected |
|-------|----------|
| `SPREADSHEET_ID` lines | 1, tail `akVMOrCgic0` |
| `PARSER_NEWS_SPREADSHEET_ID` tail | `LijNNyn50` |
| Social effective tail | `akVMOrCgic0` |
| `spreadsheet_access` | OK |
| `Social_Applications_tab` | YES |

---

## Option B — script from release branch (read-only)

```bash
# From workstation (no prod app change):
scp automation/production/prod_social_readiness_check.sh user@prod:/tmp/
ssh user@prod 'sudo bash /tmp/prod_social_readiness_check.sh'
```

Or after PR #48 merge (before flags ON):

```bash
sudo bash /var/www/mywave/automation/production/prod_social_readiness_check.sh
```

---

## Option C — after merge, before flags

Less preferred: deploy PR #48 code first, run script from `automation/production/`, then apply `SOCIAL_*` flags and restart.

---

## Does not

- Write `.env`
- Restart `mywave-site`
- Mutate Sheets
- Enable Social flags
