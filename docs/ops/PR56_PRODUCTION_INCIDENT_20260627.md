# PR56 Production Incident Report — 2026-06-27

**Status:** RESOLVED (production restored on PR55 baseline)  
**Severity:** P1 (site down, HTTP 502)  
**Duration:** crash loop until `.env` permissions fixed  
**Owner action:** emergency rollback + runtime permission repair  

---

## Executive summary

PR56 was deployed to production in **safe mode** (`5216818c`, `SOCIAL_BOOKING_ENABLED=false`). Initial smoke **PASS**. During follow-up `ADMIN_TOKEN` setup, `.env` was locked with `chmod 600` (root-only). The `mywave-site` service runs as `www-data` and loads `.env` via `load_dotenv()` in `main.py` at import time. Gunicorn workers failed with `PermissionError`, causing **502** and systemd auto-restart loop.

**Root cause:** broken `.env` permission contract — not PR56 business logic, not Google API, not disk (after cleanup), not Docker.

**Recovery:** `git reset --hard c35d19cc` (PR55) + fix `.env` to `root:www-data` mode `640` + writable `logs/` / `instance/` for `www-data`.

---

## Timeline (UTC+3, approximate)

| Phase | State |
|-------|--------|
| Pre-incident | Disk full (`0` free) — backup failed |
| Cleanup | ~15–18G free after journal/backup cleanup |
| PR56 deploy | `HEAD=5216818c`, smoke OK, assign → `503` (expected) |
| ADMIN_TOKEN setup | `.env` set to `chmod 600` |
| Outage | `PermissionError: /var/www/mywave/.env`, gunicorn `status=3`, HTTP 502 |
| Rollback | `git reset --hard c35d19cc` — site still down (permissions) |
| Fix | `chown root:www-data .env`, `chmod 640 .env`, runtime dirs for `www-data` |
| Restored | `IMPORT_OK_AS_RUN_USER`, health OK, `/social` 200 |

---

## Root cause analysis

```text
Service user:  www-data  (mywave-site.service)
App boot:      main.py → load_dotenv() → reads /var/www/mywave/.env
Failure mode:  chmod 600 .env → only root can read
Symptom:       PermissionError → worker failed to boot → 502
```

PR56 code review: **no import-time side effects** in `social_sessions.py`. Routes are registered lazily; assign/status gated by feature flags + `ADMIN_TOKEN`. Rollback to PR55 did not fix outage → confirms runtime permissions, not PR56 logic.

---

## Diagnostic artifacts (on server)

```text
/var/www/mywave/logs/rollback_pr56/status_before_20260627_054131.log
/var/www/mywave/logs/rollback_pr56/journal_before_20260627_054131.log
/var/www/mywave/logs/rollback_pr56/app_before_20260627_054131.log
```

**Expected journal pattern:**

```text
PermissionError: [Errno 13] Permission denied: '/var/www/mywave/.env'
gunicorn: Worker failed to boot
systemd: mywave-site.service: Main process exited, code=exited, status=3
```

---

## Current production state (post-recovery)

```text
Production HEAD:     c35d19cc  (PR55)
origin/main HEAD:    5216818c  (PR56 merged — NOT on prod)
SOCIAL_BOOKING_ENABLED: false
ADMIN_TOKEN:         MISSING
Manual assign:       NOT ENABLED
Service:             active
/health/live:        ok
/social:             200
```

**Do not `git pull` on prod** until controlled PR56 re-rollout (would restore `5216818c`).

---

## Corrective actions (this hotfix)

| Action | Deliverable |
|--------|-------------|
| `.env` permissions contract in runbook | `docs/deployment/TIMEWEB_PRODUCTION_RUNBOOK.md` |
| Safe ADMIN_TOKEN setup script | `automation/production/prod_admin_token_setup.sh` |
| Pre-restart `.env` + import checks | `prod_env_readable_check.sh`, `prod_import_as_run_user.sh` |
| PR56 two-phase rollout | `docs/integration/PR56_PRODUCTION_ROLLOUT_RUNBOOK.md` |
| PR56 smoke suite | `automation/production/prod_pr56_smoke.sh` |
| Sheets headers probe | `automation/production/prod_social_sessions_headers_check.sh` |

---

## Security follow-up (Owner)

If secrets were exposed in chat/logs/tools during incident response, plan rotation (values **never** in reports):

- OpenAI API key  
- Telegram bot tokens  
- Admin credentials  
- `SECRET_KEY` (if compromised)  
- Any keys from `.env`  

---

## Lessons learned

1. **Never `chmod 600 .env`** for Flask/Gunicorn services running as non-root. Use **`root:www-data` + `640`**.
2. **Check permissions before code rollback** — rollback does not fix permission regressions.
3. **Pre-restart gate:** import as service user + `.env` readable check (mandatory after any `.env` edit).
4. **PR56 safe mode first:** deploy code with `SOCIAL_BOOKING_ENABLED=false`; enable manual assign only in Phase B.

---

## Approval for re-rollout

Re-rollout requires explicit Owner approval after hotfix merge:

```text
PR56 RE-ROLLOUT PHASE A APPROVED
```

Then separately for manual assign:

```text
PR56 RE-ROLLOUT PHASE B APPROVED
```
