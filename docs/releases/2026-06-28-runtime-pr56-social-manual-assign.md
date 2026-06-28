# Release: runtime — PR56 Social manual assign

| Field | Value |
|-------|-------|
| Date | 2026-06-28 |
| Release type | runtime |
| Commit | `3b70a038` |
| Rollback commit (code) | `c35d19cc` (PR55 only — use if boot failure) |
| Rollback commit (safe mode) | keep `3b70a038`, set `SOCIAL_BOOKING_ENABLED=false` |
| Deployer | Owner |
| Smoke | PASS |
| Mobile QA | N/A |

## Summary

PR56 enables **manual** social session assign only: admin links `Social_Applications.application_id` → `Social_Sessions` via protected API. Public `/social` does **not** auto-book or create Calendar events. PR66 auth-fix ensures `401` before payload validation when `X-Admin-Token` is missing or invalid.

**Status: CLOSED.** No further deploy actions required except post-release QA observation (1–2 days).

## Scope (layer)

- [x] Runtime Foundation — PR56 sessions, audit log, admin API
- [x] Ops / Observability — PR64 prod scripts, PR66 auth, alignment evidence
- [ ] Frontend UX — admin UI out of scope (PR56)
- [ ] Content Pipeline — N/A

## Production evidence

| Check | Result |
|-------|--------|
| Production HEAD | `3b70a038` |
| PR66 merged/deployed | YES |
| Manual social assign enabled | YES |
| `SOCIAL_BOOKING_ENABLED` | `true` |
| `ADMIN_TOKEN` | SET |
| Security smoke | `no_token=401`, `bad_token=401` |
| PR56 smoke (`--phase-b`) | PASS |
| Social_Sessions headers | OK |
| Social_Audit_Log headers | OK |
| Controlled assign | HTTP `201` |
| Telegram sanitized notification | OK |

Controlled assign test:

```text
application_id=soc_app_e7be01a15ded4365
session_id=soc_sess_e41e448019644a73
status=scheduled
Social_Sessions row=YES
Social_Audit_Log rows=2
Social_Applications status=scheduled YES
```

Telegram: IDs + date/time/location + status only — no health/PII.

Detail: [docs/evidence/pr56/README.md](../evidence/pr56/README.md)

## Phases closed

```text
Phase A (safe mode deploy):           CLOSED / PASS
PR65 tabs (Sheets headers):           CLOSED / PASS
Phase B (controlled assign):          CLOSED / PASS
PR66 auth-fix merge + alignment:      CLOSED / PASS
Production alignment (clean git):     CLOSED / PASS
```

## Operational contract (production)

```text
SOCIAL_BOOKING_ENABLED=true   — do not disable without rollback approval
ADMIN_TOKEN=SET               — do not print; use prod_env_readable_check.sh
.env permissions: root:www-data 640 after any .env edit
Restart: mywave-site only
Do not touch: node, TGbotAdmin, Docker, apt, reboot, static/downloads/
```

## Rollback

**Safe mode (preferred):**

```bash
cd /var/www/mywave
sed -i 's/^SOCIAL_BOOKING_ENABLED=.*/SOCIAL_BOOKING_ENABLED=false/' .env
bash automation/production/prod_env_permissions_fix.sh
bash automation/production/prod_import_as_run_user.sh
systemctl restart mywave-site
bash automation/production/prod_pr56_smoke.sh
```

**Code rollback** (`c35d19cc`): only if `IMPORT_OK_AS_RUN_USER` fails or persistent 502.

Runbook: [PR56_PRODUCTION_ROLLOUT_RUNBOOK.md](../integration/PR56_PRODUCTION_ROLLOUT_RUNBOOK.md)  
Incident: [PR56_PRODUCTION_INCIDENT_20260627.md](../ops/PR56_PRODUCTION_INCIDENT_20260627.md)

## Post-release QA (1–2 days)

- [ ] `/social` apply → `Social_Applications` row, no Calendar write
- [ ] Assign without token → `401`
- [ ] Assign with bad token → `401`
- [ ] Manual assign with valid token → `201`, Sheets + audit rows
- [ ] Telegram without health/PII
- [ ] Commercial booking `/api/calendar/slots` unchanged

## Follow-ups (not blocking)

- PR67: post-release hardening (docs, smoke, regression tests)
- Admin UX for social assign workflow (product)
- Notifications v2 (Telegram templates + actions)
- Social project v2.1 (public page, stats — separate approval)
