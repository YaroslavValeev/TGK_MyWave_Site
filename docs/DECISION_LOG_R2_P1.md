# Decision Log: R2/P1 — Review workflow, writeback, CONTRACT (сайт)

**Дата:** 2026-01-28  
**Owner:** Сайт (Site MyWave)  
**Статус:** Реализовано (ожидание деплоя и приёмки)

---

## Контекст

После закрытия P0 (контракт raw_feed, row_number, canonical_url, ownership) в P1 добавлены:
- approve-gate перед публикацией (review_queue без approve → не публикуем),
- writeback после публикации: снятие с review_queue и при необходимости final_version,
- read-only поддержка листа CONTRACT (опционально).

---

## Принятые решения P1.0

### 1. Approve-gate (review workflow)

**Правило:** В `publish_ready_posts()` перед публикацией проверяем:
- если `review_queue` = TRUE (или 1/YES/ДА) и при этом нет approve (`approved_by` и `approved_at` пустые) → запись **не публикуется**;
- только логируем `WAITING_REVIEW`; `publish_error` не ставим, `publish_attempts` не увеличиваем, статус записи не меняем;
- если approve есть (заполнен `approved_by` или `approved_at`) → публикация разрешена.

**Файл/функция:** `app/services/blog/publish.py` → `publish_ready_posts()` (после проверки `scheduled_at`, перед `_is_publishable()`).

**DoD:** Ни один пост из raw_feed не уходит в /blog без ручного approve, если запись в review_queue. Тест: запись с `review_queue=TRUE` и пустыми `approved_by`/`approved_at` не публикуется и не портит статус/attempts.

---

### 2. Writeback после публикации (P1.0)

**Правило:** После успешной публикации в `ack_publish()` дополнительно к P0-полям:
- записать **review_queue = FALSE** (снять с очереди), если колонка существует;
- **approved_*** не трогаем (ownership не меняем);
- **final_version:** если колонка существует и по контракту SITE-owned — заполнить минимально безопасно: `published:{slug}`; иначе не трогать.

**Реализация:** В `ack_publish()` добавлены два блока обновлений (только batchUpdate по конкретным диапазонам):
1. `review_queue_col` → значение `"FALSE"`;
2. `final_version_col` → значение `f"published:{effective_slug}"` (только если колонка есть и effective_slug не пустой).

**DoD:** Опубликованные записи автоматически выходят из review_queue (колонка review_queue = FALSE).

---

### 3. CONTRACT-лист: read-only поддержка

**Правило:**
- Если лист CONTRACT появился (его создаёт Bot) — сайт может **читать** его для диагностики/логов/валидации, но **не изменяет** его.
- Если CONTRACT отсутствует — сайт не ломается, работа идёт по headers raw_feed как в P0.

**Реализация:**
- Функция `_read_contract_if_present(spreadsheet_id, logger)` в `app/services/blog/publish.py`: вызывает `read_sheet(spreadsheet_id, "CONTRACT")`; при исключении (лист не найден и т.п.) возвращает `None` и логирует на уровне debug.
- В `publish_ready_posts()` в начале прогона опционально вызывается эта функция; при успехе логируется «CONTRACT присутствует» (read-only), при отсутствии — «работаем по headers raw_feed». Логика валидации и writeback по-прежнему опирается только на raw_feed.

**DoD:** CONTRACT не является обязательным для запуска; при его наличии сайт только читает и логирует, не пишет.

---

## Ownership (критично)

Сайт пишет только:
- **P0:** publish_* + canonical_url;
- **P1:** review_queue = FALSE (после публикации), при необходимости final_version (SITE-owned).

Никаких update «всю строку целиком» — только **batchUpdate** по конкретным диапазонам (колонка + row_number).

---

## Ссылки

- P0: `docs/DECISION_LOG_R2_P0.md`
- План P1: `docs/P1_PLAN_AND_STATUS.md`
- Статус P1: `docs/P1_STATUS.md`
