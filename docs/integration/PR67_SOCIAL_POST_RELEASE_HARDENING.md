# PR67 — Social manual assign post-release hardening (proposal)

**Prerequisite:** PR56 production CLOSED / PASS (`3b70a038`)  
**Status:** IMPLEMENTED in **PR #68** (`feature/pr68-social-post-release-hardening`)  
**Risk level:** Low (docs + tests + smoke only)

> GitHub PR #67 was used for docs-only closure. Implementation PR is **#68**.

## Goal

Stabilize PR56 after successful production rollout. No new booking behavior, no admin UI implementation.

## Scope (PR68)

| # | Item | Type | Doc / path |
|---|------|------|------------|
| 1 | Release evidence docs | docs | merged in PR #67 |
| 2 | Telegram + sheets headers regression tests | tests | `tests/unit/test_pr56_telegram_regression.py`, `test_pr56_sheets_headers_regression.py` |
| 3 | `prod_pr56_smoke.sh` — `bad_token` check in `--phase-b` | scripts | `automation/production/prod_pr56_smoke.sh` |
| 4 | Rollback / safe-mode reference | docs | [PR56_ROLLBACK_SAFE_MODE.md](PR56_ROLLBACK_SAFE_MODE.md) |
| 5 | Admin workflow spec (no UI) | docs | [SOCIAL_ADMIN_ASSIGN_WORKFLOW_SPEC.md](SOCIAL_ADMIN_ASSIGN_WORKFLOW_SPEC.md) |
| 6 | Post-release QA checklist | docs | [PR56_POST_RELEASE_QA_CHECKLIST.md](PR56_POST_RELEASE_QA_CHECKLIST.md) |

## Out of scope

- Admin UI implementation
- Auto calendar booking from public form
- `SOCIAL_PUBLIC_STATS_ENABLED` without approval
- TGbotAdmin changes
- `.env` / production deploy

## Admin workflow spec (draft — product input)

**List view:** Social applications filtered by `new` / `review` / `approved` / `scheduled`

**Assign action fields:**

- `session_date`, `session_time`, `location`, `coach`, `service_type`, `notes`
- Confirm dialog before submit
- Show `session_id` on success
- Audit trail visible per `application_id`

**API mapping:** existing `POST /api/social/sessions/assign` + `PATCH .../status`

## Regression tests to add

```text
1. Boot: .env readable by www-data (documented check)
2. Auth-first: invalid payload + no token → 401 (not 400)
3. Booking flag OFF → assign 503
4. Telegram formatter: no health_notes in session scheduled message
5. Sheets headers contract unchanged
```

## Acceptance

- CI green
- No production deploy required for merge
- Owner post-release QA checklist tracked in release notes
