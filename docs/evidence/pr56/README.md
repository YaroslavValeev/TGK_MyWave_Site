# PR56 — Social manual assign — Production Evidence

**Status:** CLOSED / PASS  
**Production HEAD:** `3b70a038` (`3b70a038d9c3639b23f1d8dd862c55cbe24cd868`)  
**Alignment date:** 2026-06-28

## PR chain

| PR | Commit | Role |
|----|--------|------|
| #63 PR56 | `5216818c` / `66145d20` | Manual assign API, Social_Sessions, audit log |
| #64 | `716d81c0` | Prod runbook, `.env` permissions scripts |
| #65 | `75c44636` (branch only) | Sheets tabs script — tabs created on prod manually |
| #66 | `3b70a038` / `0d93edee` | Auth-fix: `401` before validation, `ADMIN_TOKEN` from env |

## Production runtime

```text
HEAD=3b70a038
mywave-site=active
ADMIN_TOKEN=SET
SOCIAL_BOOKING_ENABLED=true
manual assign=ENABLED
health/live=ok
health/ready=ok
.env=root:www-data 640
git_status=?? static/downloads/ only (known runtime/untracked)
```

## Smoke results (alignment 2026-06-28)

```text
PR56_SMOKE (--phase-b)=PASS
HEADERS_CHECK=COMPLETE
no_token=401
bad_token=401
assign_no_token=401
```

## Controlled assign (Phase B)

```text
application_id=soc_app_e7be01a15ded4365
session_id=soc_sess_e41e448019644a73
manual_assign_http=201
status=scheduled
Social_Sessions row=YES
Social_Audit_Log rows=YES (count=2)
Social_Applications status=scheduled YES
Telegram notification=sanitized YES
```

Telegram content verified: `application_id`, `session_id`, date, time, location, `status=scheduled`.  
Excluded: health_notes, diagnosis, parent phone/name, PII.

## Security

- Public `/api/social/apply` — no assign, no Calendar write
- Assign endpoint gated: `SOCIAL_BOOKING_ENABLED` + `X-Admin-Token`
- Auth runs **before** payload validation (PR66)

## Incident reference

Phase B first attempt failed security smoke (`400` not `401`) due to auth bypass + invalid smoke payload.  
Resolved by PR66 + safe rollback + re-run.  
See [PR56_PRODUCTION_INCIDENT_20260627.md](../../ops/PR56_PRODUCTION_INCIDENT_20260627.md).

## Owner scripts used

```text
automation/production/prod_env_permissions_fix.sh
automation/production/prod_env_readable_check.sh
automation/production/prod_import_as_run_user.sh
automation/production/prod_pr56_smoke.sh
automation/production/prod_social_sessions_headers_check.sh
automation/production/prod_admin_token_setup.sh
```

## No further deploy required

PR56 rollout complete. Monitor post-release QA checklist in release notes only.
