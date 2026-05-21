# Competitions Ticker Contract v1 (Parser News ↔ Site)

Канон для бегущей строки соревнований на главной **mywavewake.ru**.

**Реализация на сайте:** `app/services/competitions/visibility.py`, `app/services/competitions/store.py`.

**Связанные документы:** блог — `docs/BLOG_CONTRACT_v1.md`, таблица — `PARSER_NEWS_SPREADSHEET_ID` + лист `competitions_ticker`.

---

## 1. Таблица и лист

| Параметр | Значение |
|----------|----------|
| Spreadsheet ID | `PARSER_NEWS_SPREADSHEET_ID` (та же таблица, что `raw_feed`) |
| Лист | `COMPETITIONS_SHEET_NAME` (default: `competitions_ticker`) |
| Строка 1 | Заголовки колонок, без merge cells |

---

## 2. Обязательные колонки

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | string | Стабильный ключ (UUID или `{source}_{external_id}`) |
| `status` | enum | `ACTIVE` — витрина; `DRAFT` — черновик; `ARCHIVED` — скрыть |
| `discipline` | enum | `wakesurf` \| `wakeboard` \| `both` |
| `event_name` | string | Название соревнования |
| `location` | string | Город/регион |
| `country` | string | Страна |
| `start_date` | date | `YYYY-MM-DD` |
| `end_date` | date | `YYYY-MM-DD` (однодневное: `end_date = start_date`) |
| `event_url` | url | Официальная страница (приоритет ссылки в ticker) |
| `source_name` | string | Источник (IWWF, WSWS, …) |
| `source_url` | url | URL источника |
| `updated_at` | datetime | ISO 8601 |

### Рекомендуемые (parser-side)

| Колонка | Назначение |
|---------|------------|
| `ingest_status` | `new` / `parsed` / `error` |
| `ingest_error` | Текст ошибки |
| `checksum` | Идемпотентный upsert |
| `raw_title` | Оригинальный заголовок |
| `ticker_text` | Готовая строка для marquee; если пусто — сайт соберёт сам |

---

## 3. Видимость на сайте (Ticker v1)

Строка показывается, если **все** условия:

1. `status == ACTIVE` (case-insensitive)
2. `end_date >= today` (UTC date) — предстоящие и идущие
3. Непустой `event_name` и валидный `start_date`
4. Ссылка: `event_url`, иначе `source_url` (нормализованный http/https)

**Сортировка:** `start_date` ASC, затем `event_name`.

**Авто-текст** (если `ticker_text` пуст):

`{discipline} · {event_name} · {location}, {country} · {даты}`

Пример: `Wakesurf · IWWF World Championships · Orlando, USA · 12.06–15.06.2026`

---

## 4. Parser News: операционные правила

- Upsert по `id`, без дубликатов
- После `end_date` — перевод в `ARCHIVED`
- События с датами → `competitions_ticker`; статьи/новости → `raw_feed`
- Обновление: 1–2 раза в сутки; после bulk-import — `POST /api/competitions/cache/invalidate`

---

## 5. Диагностика

- `GET /api/competitions/ticker` — JSON `{ items, count, spreadsheet_id_tail, sheet_name }`
- Логи: `spreadsheet_id_tail`, `sheet_name`, `row_count` (без полного текста полей)

---

## 6. Тестовые строки (приёмка)

| id | status | Ожидание на сайте |
|----|--------|-------------------|
| test-1 | ACTIVE, end_date в будущем | Показать |
| test-2 | ACTIVE, end_date в будущем | Показать |
| test-3 | ARCHIVED или end_date в прошлом | Скрыть |
