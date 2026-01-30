# P1: План и статус (сайт)

**Дата:** 2026-01-28  
**Контекст:** P0 закрыт с обеих сторон. Canonical: mywavetreaning.ru, путь /blog/{slug}.

---

## P1-блокер: фиксация домена в main

**Цель:** Везде формировать canonical_url строго на `https://mywavetreaning.ru`.

**Сделано:**
- В `app/services/blog/publish.py` fallback в `_get_public_blog_base_url()` задан как `https://mywavetreaning.ru`.

**DoD:**
- [ ] Изменение закоммичено
- [ ] Запушено в main
- [ ] Попало в деплой

---

## P1.0: Review workflow — approve-gate

**Цель:** Ни один пост из raw_feed не уходит в /blog без ручного approve, если запись в review_queue.

**Реализовано в `publish_ready_posts()`:**
- Если `review_queue` = TRUE (или 1/YES/ДА) и нет approve (`approved_by` и `approved_at` пустые) → запись **не публикуется**, только логируется `WAITING_REVIEW`.
- `publish_error` не ставится, `publish_attempts` не увеличиваются, статус записи не меняется.
- Если approve есть (заполнен `approved_by` или `approved_at`) → публикация разрешена.

**Колонки в raw_feed:** `review_queue`, `approved_by`, `approved_at` (ожидаются в таблице; если колонок нет, запись считается «без review_queue» и публикуется по прежним правилам).

**DoD:**
- [x] Правило добавлено в код
- [ ] Проверено на проде (запись в review_queue без approve не публикуется)

---

## P1.0: Writeback после публикации

**Реализовано в `ack_publish()` (дополнительно к P0):**
- **review_queue = FALSE** — снять запись с очереди (если колонка существует). approved_* не трогаем.
- **final_version** — если колонка существует и SITE-owned: запись минимально безопасно `published:{slug}`; иначе не трогаем.

Только batchUpdate по конкретным диапазонам (колонка + row_number), без обновления всей строки.

**DoD:** Опубликованные записи автоматически выходят из review_queue.

---

## P1.0: CONTRACT-лист read-only

**Реализовано:**
- Функция `_read_contract_if_present(spreadsheet_id, logger)` — опционально читает лист CONTRACT; при отсутствии/ошибке возвращает None, не ломает работу.
- В `publish_ready_posts()` в начале прогона — вызов и лог «CONTRACT присутствует» или «работаем по headers raw_feed». Сайт CONTRACT не изменяет.

**DoD:** CONTRACT не обязателен для запуска; при наличии — только чтение и логирование.

---

## Разделение задач (subagents)

- **Sheets/Workflow:** логика publish_ready_posts, review_queue, approve-gate (сделано в этом коммите).
- **Docs/QA:** документация P1, чеклисты, приёмка на проде.
- **Infra/Redirects:** деплой, 301-редиректы, SERVER_NAME (по необходимости).

---

## Ссылки

- Decision Log R2/P0: `docs/DECISION_LOG_R2_P0.md`
- P0 Deployment Status: `docs/P0_DEPLOYMENT_STATUS.md`
