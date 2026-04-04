# BLOG Canonical Mapping

Документ фиксирует единый контракт поста для витрины сайта и правила нормализации legacy-полей.

**Правило попадания строки из Sheets на витрину (publishable v1):** см. [BLOG_CONTRACT_v1.md](../BLOG_CONTRACT_v1.md).

## 1. Текущее корректное состояние

- Витрина блога (`/blog`) и блок блога на главной используют один путь:
  - `app/routes/blog.py` -> `app.services.blog.store.get_posts(...)`
  - `app/__init__.py` (route `/`) -> `app.services.blog.store.get_posts(page=1, limit=4, ...)`
- Источник данных:
  - `primary`: Google Sheets (`raw_feed`, через `PARSER_TAB`)
  - `fallback`: локальная БД (`blog_post`)
- XLSX-дамп (`MyWave_Parser_News.xlsx`) не является прямым runtime-источником сайта.

## 2. Canonical post contract (site read model)

Ниже каноническая структура поста для рендера витрины:

- `title`
- `slug`
- `excerpt`
- `content_md`
- `content_html`
- `cover_image_url`
- `tags` (list[str])
- `status`
- `published_at`
- `updated_at` (если доступно на уровне источника/БД)
- `source_name`
- `source_url`

Примечание: в БД есть дополнительные технические поля (`id`, `checksum`, `sheet_row_number`, ...), но они не являются обязательными полями витринного read model.

## 3. Legacy -> canonical mapping

Нормализация (фактическая и требуемая) для данных из `raw_feed`:

- `raw_title` -> `title` (если `title` отсутствует)
- `summary` -> `excerpt`
- `lead` -> `excerpt` (fallback, если `summary` пуст)
- `final_posts` -> `content_md`
- `text` -> `content_md` (fallback, если `final_posts` пуст)
- `content_md` -> `content_html` (через markdown + sanitize)
- `cover_image_url` -> `cover_image_url`
- `image_url` -> `cover_image_url` (fallback)
- `raw_media` -> `cover_image_url` (fallback второго уровня)
- `raw_tags`/`tags`/`ne` -> `tags`

## 4. Publish rules (current)

Пост считается публикуемым (видимым в витрине), если выполняется одно из условий:

- `status in {READY_TO_PUBLISH, PUBLISHED, published}`
- `published_posts = TRUE`

### Важные уточнения

- `APPROVED` сам по себе **не** считается опубликованным статусом.
- `ingest_status` (например `OK`) не равен editorial publish-статусу и не должен напрямую открывать запись в витрине.
- Не расширять `_is_publishable()` на "все строки с контентом" без отдельного решения по редакционной политике.

## 5. Слои данных (as-is)

Сейчас в `raw_feed` смешаны:

- ingest-атрибуты
- editorial-статусы
- витринные поля

Это допустимо для MVP, но приводит к риску рассинхрона. Нормализация выполняется в коде эвристически (`store._normalize_row_from_sheets(...)`), а не через отдельный строго типизированный ingestion layer.

## 6. Политика по XLSX

`MyWave_Parser_News.xlsx` использовать только через адаптер импорта:

1. определить корректные заголовки,
2. привести поля к canonical columns,
3. загрузить в `raw_feed`/целевой лист,
4. отдельно управлять publish-сигналами (`status`, `published_posts`).

Прямое чтение XLSX как runtime-источника сайта не допускается.

## 7. Что не меняем этим документом

- Не меняем текущий источник витрины (`raw_feed` + fallback DB).
- Не меняем текущие publish-правила.
- Не переводим сайт на чтение `news_articles` в рамках этого шага.
