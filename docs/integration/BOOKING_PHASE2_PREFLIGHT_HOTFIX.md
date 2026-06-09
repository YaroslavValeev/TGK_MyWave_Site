# BOOKING Phase 2 — Preflight Hotfix Package (GM)

**From:** Site MyWave  
**To:** GM / TGbotAdmin  
**Date:** 2026-06-09  
**Commit:** `ce965fc235960dbfe585e0239a908a9386d31cf5`  
**Status:** **APPLIED ON PRODUCTION — `PREFLIGHT_OK` CONFIRMED**

---

## 1. Root cause

### Symptom

```text
SyntaxError: invalid decimal literal
  File "/var/www/mywave/.env", line 31
    SPREADSHEET_ID=1RJpw2mAMej3a-VC6yKAsKkVQvzGStcjUC7LijNNyn50
```

### Why `.env` was executed as Python

Broken invocation (pre-`ce965fc2`):

```bash
python3 <<'PY' "${ENV_FILE}" ...
```

In bash, arguments after `<<'PY'` are passed to `python3` as **script file names**, not as stdin modifiers. Python therefore **opened and executed** `/var/www/mywave/.env` as source code. Line `SPREADSHEET_ID=1RJpw2m…` is invalid Python → `SyntaxError`.

The heredoc body was **not** used as the program; `.env` was.

### Fix

Correct pattern:

```bash
python3 - "${ENV_FILE}" ... <<'PY'
# parser reads path from sys.argv[1], opens file explicitly
PY
```

`-` tells Python to read the **script from stdin** (heredoc). `.env` is only read via `open(path)` inside the parser — never executed.

Same bug class fixed for `/health` JSON check (`python3 <<'PY' /tmp/...json` → `python3 - /tmp/...json <<'PY'`).

### Secondary fixes (same commit)

| Issue | Fix |
|-------|-----|
| `www-data` cannot write `.git/FETCH_HEAD` | `git fetch` as root with `git -c safe.directory=…` |
| Health `database`/`google` shape | Read `checks.database.ok` / `checks.google.ok` |
| Missing route checks | Added `/`, `/robots.txt`, `/privacy`, `/offer` HTTP 200 |

---

## 2. Diff summary

| Path | Change |
|------|--------|
| `automation/production/phase2_preflight_readonly.sh` | **Only runtime-touching file** (read-only script) |
| `docs/integration/BOOKING_PHASE2_PREFLIGHT_HOTFIX.md` | This document |

**Not changed:** `app/`, `templates/`, `static/`, production `.env`, `BOOKING_PHASE2_*`, Calendar/Sheet IDs.

**Prior commits in chain:** `b7726d41` (first heredoc fix), `e11a087d` (executable bit), `ce965fc2` (full hotfix + routes + health parser).

---

## 3. Validation

### Local syntax

```bash
bash -n automation/production/phase2_preflight_readonly.sh
```

### Production rerun (read-only; no restart)

```bash
cd /var/www/mywave
git -c safe.directory=/var/www/mywave pull --ff-only origin main
bash automation/production/phase2_preflight_readonly.sh | tee /tmp/prod_phase2_preflight_after_hotfix.log
```

### Production result (Owner, 2026-06-09 ~13:40 MSK)

| Check | Result |
|-------|--------|
| HEAD | `ce965fc2` >= `27f2d886` |
| Effective `SPREADSHEET_ID` | `…VMOrCgic0` (last-wins) |
| Staging IDs | PASS |
| `BOOKING_PHASE2_*` | absent |
| `/health` | 200, database OK, google OK |
| Public routes | 200 |
| **Marker** | **`PREFLIGHT_OK`** |

Log: `/tmp/prod_phase2_preflight_after_hotfix.log`

**WARN (non-blocking):** duplicate `SPREADSHEET_ID` lines L31/L36 in `.env`; effective = booking sheet.

---

## 4. Guardrails (hotfix)

| Rule | Status |
|------|--------|
| Restart required for hotfix | **No** (script-only pull) |
| `mywave-site` restart | **Not required** for hotfix |
| `mywave-node.service` | **Not touched** |
| `mywave-telegram-bot.service` | **Not touched** |
| TGbotAdmin production | **Not touched** |
| Production `.env` | **Not changed** |
| `BOOKING_PHASE2_*` | **Not enabled** |
| Calendar/Sheet IDs | **Not changed** |

---

## 5. GM gate status

| Gate | Status |
|------|--------|
| CODE-ONLY deploy | **PASS** (`b7f8372a` → current `ce965fc2`) |
| Preflight hotfix | **PASS** (`PREFLIGHT_OK`) |
| Step 1 `BOOKING_PHASE2_AVAILABILITY=1` | **NOT APPROVED** — await written GM approval |

After written approval: [`BOOKING_PHASE2_PRODUCTION_FLAG_ROLLOUT_PACKAGE.md`](BOOKING_PHASE2_PRODUCTION_FLAG_ROLLOUT_PACKAGE.md) §6.2 Step 1 only.
