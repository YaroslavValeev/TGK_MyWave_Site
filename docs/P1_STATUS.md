# P1: Статус (сайт)

**Дата обновления:** 2026-01-28

---

## P1-блокер: фиксация домена в main

**Цель:** canonical_url строго на `https://mywavetreaning.ru`.

**Код:** `app/services/blog/publish.py` → `_get_public_blog_base_url()`: fallback = `"https://mywavetreaning.ru"`.

**Статус:** Реализовано в коде. DoD: закоммичено, запушено в main, попало в деплой.

---

## P1.0: Review workflow — approve-gate

**Цель:** Не публиковать записи из review_queue без ручного approve.

**Код:** `app/services/blog/publish.py` → `publish_ready_posts()`: проверка `review_queue` + `approved_by`/`approved_at`; при отсутствии approve — skip с логом WAITING_REVIEW (без publish_error и без инкремента attempts).

**DoD-тест:** Запись с `review_queue=TRUE` и пустыми `approved_by`/`approved_at` не публикуется и не портит статус/attempts.

---

## P1.0: Writeback после публикации

**Цель:** Опубликованные записи автоматически выходят из review_queue; при необходимости заполняется final_version.

**Код:** `app/services/blog/publish.py` → `ack_publish()`:
- **review_queue:** если колонка есть → запись `"FALSE"` (batchUpdate по диапазону колонки + row_number).
- **final_version:** если колонка есть и есть effective_slug → запись `"published:{slug}"` (batchUpdate по диапазону).

**approved_*** не трогаем.

---

## P1.0: CONTRACT-лист read-only

**Цель:** При наличии листа CONTRACT — только читать для диагностики/логов; не изменять. При отсутствии — не ломаться.

**Код:** `app/services/blog/publish.py`:
- `_read_contract_if_present(spreadsheet_id, logger)` — опциональное чтение листа "CONTRACT"; при ошибке возврат None.
- В `publish_ready_posts()` в начале — вызов и лог «CONTRACT присутствует» / «работаем по raw_feed».

---

## Документация P1

- **Decision Log R2/P1:** `docs/DECISION_LOG_R2_P1.md`
- **План и детали:** `docs/P1_PLAN_AND_STATUS.md`
- **Статус:** этот файл `docs/P1_STATUS.md`

DoD: P1 закреплён документально (approve-gate, writeback, CONTRACT, ownership).
