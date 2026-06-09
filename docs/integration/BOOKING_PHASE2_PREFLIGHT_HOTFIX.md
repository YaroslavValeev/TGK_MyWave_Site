# BOOKING Phase 2 — Preflight hotfix (read-only)

**Date:** 2026-06-09  
**Scope:** `automation/production/phase2_preflight_readonly.sh` only  
**Production:** no `.env` change, no flags, no restart required for hotfix pull

## Problem

`python3 <<'PY' "${ENV_FILE}"` caused Python to execute `.env` as source → `SyntaxError: invalid decimal literal` on `SPREADSHEET_ID=1RJpw2m…`.

## Fix

- Use `python3 - "${ENV_FILE}" … <<'PY'` — stdin is script, argv[1] is dotenv path.
- Same fix for health JSON parser.
- Parse `database.ok` / `google.ok` from `/health` JSON (not `.status` subfield).
- Git read/fetch as root with `git -c safe.directory=…` (no `www-data` FETCH_HEAD error).
- Added public routes check: `/`, `/robots.txt`, `/privacy`, `/offer`.

## Apply on production (read-only pull)

```bash
cd /var/www/mywave
git -c safe.directory=/var/www/mywave fetch origin main
git -c safe.directory=/var/www/mywave pull --ff-only origin main
bash automation/production/phase2_preflight_readonly.sh | tee /tmp/prod_phase2_preflight_after_hotfix.log
tail -3 /tmp/prod_phase2_preflight_after_hotfix.log
```

**PASS:** `PREFLIGHT_OK`
