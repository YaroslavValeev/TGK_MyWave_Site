# PR67 — Social manual assign post-release hardening (proposal)

**Prerequisite:** PR56 production CLOSED / PASS (`3b70a038`)  
**Status:** PROPOSED — not approved for runtime  
**Risk level:** Low (docs + tests + smoke only)

## Goal

Stabilize PR56 after successful production rollout. No new booking behavior, no admin UI implementation.

## Proposed scope

| # | Item | Type |
|---|------|------|
| 1 | Release evidence docs (this repo) | docs |
| 2 | Regression tests: auth-first, sanitized Telegram, boot `.env` | tests |
| 3 | `prod_pr56_smoke.sh` — optional `bad_token` check inline | scripts |
| 4 | Rollback / safe-mode one-liner doc sync | docs |
| 5 | Admin workflow **spec** (no UI) — assign form fields, status flow | docs |

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
