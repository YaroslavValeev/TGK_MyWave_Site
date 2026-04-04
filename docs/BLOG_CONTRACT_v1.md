# Blog Contract v1 (MyWave Site ↔ Parser_News)

Утверждённое управленческое решение (GM): этот документ — **канон** для правил «показывать материал на сайте» и единой проверки publishable в коде до смены product mode.

**Реализация в коде:** `app/services/blog/publishability.py` (`is_publishable_row`, `has_publishable_content`, `is_publishable_blog_post_record`).

**Связанные документы:** маппинг полей витрины — `docs/architecture/BLOG_CANONICAL_MAPPING.md`.

---

## 1. Publishable v1 (строка из `raw_feed` / dict по заголовкам)

Материал считается **publishable** для витрины, sync, smoke-check и dry-run, если одновременно:

1. **`status`** после нормализации `str(status).strip().upper()` входит в множество  
   **`{"READY_TO_PUBLISH", "PUBLISHED"}`**.
2. Статус **не** `ARCHIVED` (явная проверка; фактически `ARCHIVED` не входит в множество выше, правило зафиксировано явно в коде).
3. Выполнено **наличие контента** (`has_publishable_content`):
   - обычно: непустое хотя бы одно из полей  
     `final_posts`, `text`, `raw_content`, `raw_html`;
   - режим, похожий на **news_articles**: если в строке есть непустой `title` и присутствует ключ `text` — требуется непустой `text`.

**Не входят** в обязательный фильтр publishable v1:

- `published_posts`
- `final_ready`
- `telegram_published`

Они могут использоваться в других процессах (например, writeback / учёт публикаций), но **не определяют**, показывать ли пост на витрине по Contract v1.

---

## 2. Статус APPROVED

**Решение:** `APPROVED` **не** считается publishable и **не** маппится на `READY_TO_PUBLISH`.

Чтобы материал появился на сайте по v1, в таблице должен быть выставлен **`READY_TO_PUBLISH`** или **`PUBLISHED`** (и выполнены условия контента из §1).

---

## 3. Политика `scheduled_at`

- **Витрина (чтение Sheets для `/blog` и главной):** по Contract v1 **`scheduled_at` не фильтрует** показ — решение о видимости на сайте опирается только на §1.
- **Publish pipeline** (`publish_ready_posts`): если в строке задано **`scheduled_at`**, запись **не обрабатывается для публикации**, пока момент времени **в будущем** относительно **`datetime.utcnow()`** после парсинга даты и приведения к **naive UTC** (`_normalize_to_naive_utc` в `app/services/blog/sync.py`).  
  Naive datetime из Sheets трактуется как уже UTC для сравнения.

---

## 4. `telegram_published`

**Пока не используется** в фильтре publishable v1. Включение отдельного product mode («только опубликовано в Telegram») — **только после согласования** и отдельного изменения кода/контракта.

---

## 5. Витрина и смена поведения

**Без согласования нового product mode** не менять:

- правила отображения списка/карточек/страницы поста;
- состав publishable v1, кроме явно согласованных правок к этому документу и `publishability.py`.

Любое расширение (например, фильтр по `telegram_published` на витрине) оформляется как **Contract v2+** или отдельный режим с обновлением этого файла.

---

## 6. Потребители одной логики в коде

Одна и та же проверка publishable v1 используется в:

- `app/services/blog/store.py` (витрина из Sheets, согласованность с БД-резервом);
- `app/services/blog/sync.py` (синхронизация в БД);
- `app/services/blog/publish.py` (pipeline публикации);
- `scripts/blog_raw_feed_smoke_check.py`;
- `scripts/blog_xlsx_dry_run_importer.py`.

---

## 7. Наблюдаемость пайплайна Parser_News (рекомендация логов)

Код записи в Sheets живёт в репозитории **Parser_News**; на стороне сайта полезно иметь **read-only** сводку по уже записанному листу (`scripts/blog_raw_feed_smoke_check.py`, поле `vitrine_quality`).

Для ускорения диагностики потерь между «входная пачка» и строками в `raw_feed` рекомендуется в **Parser_News** после каждого прогона логировать структурированно (без PII и без полного `raw_content`):

| Поле / смысл | Пример |
|----------------|--------|
| `batch_input_count` | размер входной пачки до дедупа/валидации |
| `batch_written_count` | фактически записано строк (append/update) |
| `batch_dropped_count` | отброшено = input − written (или явная сумма) |
| `drop_reasons` | счётчики по категориям: `duplicate`, `checksum`, `validate_raw_row`, `empty_row`, `api_error`, `other` |

Один лог-событие на прогон (например `parser_raw_feed_batch_summary`) с этими полями достаточно, чтобы сверять «311 vs 190» без ручного разбора.
