# Письмо команде ParserNews: лист `competitions_ticker`

**Тема:** Контракт листа `competitions_ticker` для бегущей строки соревнований на mywavewake.ru

**Кому:** команда ParserNews / Parser Bot

---

Здравствуйте!

На главной сайта **mywavewake.ru** нужна **бегущая строка** с мировыми соревнованиями по **вейксерфингу и вейкборду**. Блог уже читается из `raw_feed`. Просим наполнять **отдельный лист** в **той же таблице**.

### Таблица и лист

- **Spreadsheet ID:** `1RJpw2mAMej3a-VC6yKAsKkVQvzGStcjUC7LijNNyn50`
- **Лист:** `competitions_ticker`
- **Строка 1:** заголовки без merge cells

### Колонки (обязательные)

```
id | status | discipline | event_name | location | country | start_date | end_date | event_url | source_name | source_url | updated_at
```

Рекомендуемые: `ingest_status`, `ingest_error`, `checksum`, `raw_title`, `ticker_text`.

### Семантика

- **`id`** — стабильный ключ; upsert по `id`
- **`status`:** `ACTIVE` = на сайте; `DRAFT` = черновик; `ARCHIVED` = скрыть
- **`discipline`:** `wakesurf` | `wakeboard` | `both`
- **Даты:** `YYYY-MM-DD`; однодневное: `end_date = start_date`
- **`event_url`** — ссылка в ticker (приоритет); иначе `source_url`

### Что показывает сайт

- `status=ACTIVE` и `end_date >= сегодня`
- Клик → `event_url` или `source_url`
- Если `ticker_text` заполнен — используем его

### Источники

**Wakesurf:** IWWF, WSWS, WWA, CWSA, ФСР, national tours.  
**Wakeboard:** IWWF wakeboard/cable, WWA, The Wakeboard Tour, cable contests.

События с датами → `competitions_ticker`; статьи → `raw_feed`.

### Операции

- Дедуп по `id` / `checksum`
- После `end_date` → `ARCHIVED`
- Обновление 1–2 раза в сутки
- После bulk-import: `POST https://mywavewake.ru/api/competitions/cache/invalidate` (Bearer `MEDIA_UPLOAD_TOKEN`)

### Приёмка (3 тестовые строки)

| id | status | Ожидание |
|----|--------|----------|
| test-1 | ACTIVE, даты в будущем | Показать |
| test-2 | ACTIVE, даты в будущем | Показать |
| test-3 | ARCHIVED или даты в прошлом | Скрыть |

### Документация и API

- Контракт: `docs/COMPETITIONS_TICKER_CONTRACT_v1.md`
- Диагностика: `GET https://mywavewake.ru/api/competitions/ticker`

Спасибо!
