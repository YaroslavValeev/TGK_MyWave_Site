# PR56 — Post-release QA checklist

**Window:** 1–2 days after production alignment (`3b70a038`)  
**Owner:** manual verification  
**No production deploy** required for this checklist itself.

---

## Public flow

- [ ] Форма `/social` отправляет заявку → строка в `Social_Applications`
- [ ] Публичный `/api/social/apply` **не** вызывает assign и **не** пишет в Calendar
- [ ] Статус новой заявки: `new` (или ожидаемый по контракту)

## Manual assign (admin)

- [ ] `POST /api/social/sessions/assign` без `X-Admin-Token` → **401**
- [ ] С неверным токеном → **401** (не 400)
- [ ] С валидным токеном и реальным `application_id` → **201**
- [ ] После assign: строка в `Social_Sessions`
- [ ] `Social_Applications.status` → `scheduled`
- [ ] `Social_Audit_Log`: минимум 2 записи (assign + status)

## Telegram

- [ ] Уведомление о scheduled session содержит: `application_id`, `session_id`, дата, время, локация, status
- [ ] **Нет:** health_notes, диагнозов, телефонов родителей, имён детей, motivation_text

## Sheets headers

- [ ] `Social_Sessions` — 15 колонок (контракт PR56)
- [ ] `Social_Audit_Log` — 6 колонок

## Regression (automated / scripts)

- [ ] `prod_pr56_smoke.sh --phase-b` → PASS (`no_token`, `bad_token`)
- [ ] `prod_env_readable_check.sh` → PASS (`.env` readable by `www-data`)
- [ ] CI: `test_pr56_*` green

## Safe mode (optional drill — only with approval)

- [ ] `SOCIAL_BOOKING_ENABLED=false` → assign **503**
- [ ] Re-enable → `--phase-b` smoke PASS

---

## Sign-off

| Item | Value |
|------|-------|
| Production HEAD | `3b70a038` |
| QA completed by | |
| Date | |
| Notes | |

When all items checked: PR56 post-release QA **CLOSED**.
