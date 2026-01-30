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

**Контекст:** В P0 уже реализован writeback после успешной публикации (`ack_publish()`): записываются `published_posts`, `published_at`, `canonical_url`, сброс lock, `publish_error` и т.д.

**Уточнение:** Текст задачи 3 был обрезан («После успешной публикации,»). Если под P1.0 подразумевается дополнительный writeback (например, очистка `review_queue`, запись `final_version` или иные поля) — нужно уточнить требования и добавить в этот план.

---

## Разделение задач (subagents)

- **Sheets/Workflow:** логика publish_ready_posts, review_queue, approve-gate (сделано в этом коммите).
- **Docs/QA:** документация P1, чеклисты, приёмка на проде.
- **Infra/Redirects:** деплой, 301-редиректы, SERVER_NAME (по необходимости).

---

## Ссылки

- Decision Log R2/P0: `docs/DECISION_LOG_R2_P0.md`
- P0 Deployment Status: `docs/P0_DEPLOYMENT_STATUS.md`
