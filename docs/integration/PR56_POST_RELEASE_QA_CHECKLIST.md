# PR56 — Post-release QA checklist

**Window:** 1–2 days after production alignment (`3b70a038`)  
**Status:** **CLOSED / PASS** (2026-06-29)  
**No production deploy** required for this checklist.

Monitoring log: [QA_MONITORING_LOG.md](../evidence/pr56/QA_MONITORING_LOG.md)

---

## Public flow

- [x] Публичный `/api/social/apply` **не** вызывает assign и **не** пишет в Calendar — unit regression + alignment
- [x] Форма `/social` → заявка в Sheets — verified at alignment (controlled flow); no incidents in D0–D2
- [x] Статус новой заявки: `new` — contract unchanged

## Manual assign (admin)

- [x] `POST /api/social/sessions/assign` без `X-Admin-Token` → **401** — alignment smoke
- [x] С неверным токеном → **401** (не 400) — alignment smoke
- [x] С валидным токеном и реальным `application_id` → **201** — controlled assign (alignment)
- [x] После assign: строка в `Social_Sessions` — alignment evidence
- [x] `Social_Applications.status` → `scheduled` — alignment evidence
- [x] `Social_Audit_Log`: минимум 2 записи — alignment evidence

## Telegram

- [x] Scheduled session: `application_id`, `session_id`, date, time, location, status — alignment
- [x] **Нет** health_notes, диагнозов, телефонов, motivation_text — alignment + PR68 regression tests

## Sheets headers

- [x] `Social_Sessions` — 15 колонок — alignment headers check
- [x] `Social_Audit_Log` — 6 колонок — alignment headers check

## Regression (automated / scripts)

- [x] `prod_pr56_smoke.sh --phase-b` → PASS — alignment 2026-06-28
- [x] `prod_env_readable_check.sh` → PASS — alignment 2026-06-28
- [x] CI: `test_pr56_*` green — Day 0 + PR68 in main

## Safe mode (optional drill — only with approval)

- [ ] `SOCIAL_BOOKING_ENABLED=false` → assign **503** — not drilled (not required for closure)
- [ ] Re-enable → `--phase-b` smoke PASS — not drilled

---

## Sign-off

| Item | Value |
|------|-------|
| Production HEAD | `3b70a038` |
| main (post-PR68) | `df24a4d9` |
| Day 0 | **ACCEPTED** (2026-06-28) |
| Day 1 | **ACCEPTED** (2026-06-28) |
| Day 2 | **ACCEPTED** (2026-06-29) |
| Post-release monitoring | **CLOSED / PASS** |
| QA completed by | Site team |
| Notes | No incidents D0–D2; no Owner server commands; no prod deploy |

PR56 post-release QA **CLOSED / PASS**.
