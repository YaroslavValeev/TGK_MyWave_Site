# Notifications v2 — preparation brief

**Status:** PREP (not deployed)  
**Date:** 2026-06-29  
**Authorized by:** Owner management decision (Browser QA blocked on client network; server-side PASS)

## Constraints (hard)

```text
No production deploy
No merge without Owner review
No .env changes
No feature flag changes (SOCIAL_ADMIN_NOTIFICATIONS_ENABLED stays OFF on prod until rollout approval)
No TGbotAdmin/node changes
No changes inside PR70/PR71 scope (/admin/social UI, auth templates)
```

## Current baseline (v1)

- Flag: `SOCIAL_ADMIN_NOTIFICATIONS_ENABLED` (default OFF)
- Service: `app/services/application_notifications.py`
- Hooks:
  - `notify_new_application('social')` — on apply (`app/routes/social.py`)
  - `notify_social_session_scheduled()` — on manual assign (API + admin UI when flag ON)
- Telegram: sanitized text only (no health/PII in session-scheduled message)
- Tests: `tests/unit/test_pr56_telegram_regression.py`, `test_social_features.py`

## v2 scope (draft — Owner review required)

Per release follow-up: **Telegram templates + actions**.

| Area | v2 candidate |
|------|----------------|
| Templates | Structured message templates (new application, session scheduled, status change) |
| Actions | Optional inline/deep-link actions for admin (view in Sheets / admin UI link) |
| Triggers | Align API assign + `/admin/social` assign path (same notify contract) |
| Safety | Keep sanitization rules; no health_notes / motivation_text / internal_notes in Telegram |
| Config | Extend behind existing flag or new sub-flag (proposal only — no prod `.env` change in PR) |

## Out of scope for v2 PR

- Public social page v2.1
- PR65 tabs script
- Commercial booking changes
- Browser QA closure (separate, when Owner network restored)

## Suggested PR sequence

1. **PR72 (prep):** spec + unit tests for template formatting (no prod behavior change, flag OFF)
2. **PR73+ (optional):** actions / wiring — each with Owner review
3. **Rollout:** separate runbook + flag flip approval (not in code-only PR)

## PR70 Browser QA (parallel track)

```text
PR70: DEPLOYED / SERVER-SIDE PASS / Browser QA IN PROGRESS
PR71: DEPLOYED / PASS
Production HEAD: 83daf51f
Production incident: NO
External access: restored (Owner VPN off; curl 200/302)
```

Close Browser QA when Owner completes admin UI checklist in browser.

## Backlog (not blocking PR70/PR71)

**External access reliability checklist** (future):

- test from multiple networks/ISPs
- VPN-sensitive scenarios
- HTTP/2 vs HTTP/1.1
- DNS/TTL review
- CDN/proxy/WAF decision
- no AAAA/IPv6 if IPv6 not served stably
