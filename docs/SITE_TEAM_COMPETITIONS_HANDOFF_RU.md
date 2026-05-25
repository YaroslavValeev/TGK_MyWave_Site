# Ответ Site MyWave команде Parser News (handoff `competitions_ticker`)

**Тема:** Re: Parser News — лист `competitions_ticker` готов к приёмке

**Дата:** 2026-05-21

---

Здравствуйте!

Спасибо за реализацию на стороне Parser News. Со стороны **Site MyWave** контракт **COMPETITIONS_TICKER_CONTRACT v1** принят; чтение листа, API и бегущая строка на главной **уже в коде** (ожидают деплой на prod, если ещё не выкатили последний `git pull`).

Ниже — ответы на ваши пункты проверки и согласованные детали интеграции.

---

## 1. Подтверждение endpoint’ов (без отличий от brief)

| Метод | URL | Назначение |
|-------|-----|------------|
| `GET` | `https://mywavewake.ru/api/competitions/ticker` | Список видимых событий для ticker + диагностика |
| `POST` | `https://mywavewake.ru/api/competitions/cache/invalidate` | Сброс in-memory кэша Sheets (TTL по умолчанию 300 с) |

**Других путей invalidate нет** — используйте именно `/api/competitions/cache/invalidate`.

---

## 2. Авторизация invalidate

На сайте принимается **тот же секрет**, что для media upload и сброса кэша блога:

- заголовок `Authorization: Bearer <MEDIA_UPLOAD_TOKEN>`
- или `X-Media-Upload-Token: <MEDIA_UPLOAD_TOKEN>`

Значение должно совпадать с **`MEDIA_UPLOAD_TOKEN` в `.env` процесса сайта** на сервере (`/var/www/mywave/.env`).

Опционально в `.env` сайта: `COMPETITIONS_CACHE_INVALIDATE_TOKEN` — если задан, invalidate принимает **его или** `MEDIA_UPLOAD_TOKEN` (достаточно совпадения с одним).

**403 forbidden** на invalidate обычно значит: токен в Parser `.env` **не совпадает** с `MEDIA_UPLOAD_TOKEN` в `/var/www/mywave/.env` (пробелы, кавычки, другой secret). Проверка на сервере:

```bash
# тот же запрос, что у Parser (подставьте токен с сервера)
curl -sS -o /dev/null -w "%{http_code}\n" -X POST "https://mywavewake.ru/api/competitions/cache/invalidate" \
  -H "Authorization: Bearer $(grep '^MEDIA_UPLOAD_TOKEN=' /var/www/mywave/.env | cut -d= -f2-)"
# ожидается 200
```

---

## 3. Что читает сайт из таблицы

| Параметр | Значение на prod |
|----------|------------------|
| Spreadsheet | `PARSER_NEWS_SPREADSHEET_ID` = `1RJpw2mAMej3a-VC6yKAsKkVQvzGStcjUC7LijNNyn50` |
| Лист | `COMPETITIONS_SHEET_NAME` = `competitions_ticker` (default) |
| Service Account | тот же JSON, что для `raw_feed` |

**Правила видимости (Ticker v1)** — совпадают с контрактом:

- `status == ACTIVE`
- `end_date >= today` (UTC date)
- непустые `event_name`, `start_date`
- клик: `source_url`, иначе `event_url`

**Сортировка:** `start_date` ASC, `event_name`.

**Текст:** если `ticker_text` заполнен — используем его; иначе собираем строку на сайте.

**ID тестовых строк:** в brief у нас были `test-ticker-1…3`, у вас в письме `test-1…3` — **оба варианта допустимы**, главное статусы и даты по контракту.

---

## 4. Ожидаемый результат приёмки

После `python scripts/sync_competitions_ticker.py --seed-acceptance` и invalidate:

```json
GET /api/competitions/ticker
{
  "count": 2,
  "sheet_name": "competitions_ticker",
  "spreadsheet_id_tail": "NNyn50",
  "items": [ { "id": "...", "label": "...", "href": "https://..." }, ... ]
}
```

На главной https://mywavewake.ru/ между «Проекты» и «Блог» — горизонтальная бегущая строка (если `count >= 1`).

---

## 5. Чек-лист для совместной приёмки

**Parser News:**

1. Залить seed: `python scripts/sync_competitions_ticker.py --seed-acceptance`
2. Вызвать invalidate:
   ```bash
   curl -X POST "https://mywavewake.ru/api/competitions/cache/invalidate" \
     -H "Authorization: Bearer $MEDIA_UPLOAD_TOKEN"
   ```
3. Написать в чат: «seed залит» + tail spreadsheet id при сомнениях

**Site MyWave (владелец сервера):**

1. Убедиться, что на prod выкатан код с `competitions_bp` и в `.env`:
   ```env
   PARSER_NEWS_SPREADSHEET_ID=1RJpw2mAMej3a-VC6yKAsKkVQvzGStcjUC7LijNNyn50
   COMPETITIONS_SHEET_NAME=competitions_ticker
   COMPETITIONS_SHEETS_CACHE_TTL=300
   MEDIA_UPLOAD_TOKEN=<тот же, что у Parser для invalidate>
   ```
2. `sudo systemctl restart mywave-site`
3. Проверить:
   ```bash
   curl -sS "https://mywavewake.ru/api/competitions/ticker"
   ```
4. Открыть главную с Ctrl+F5

**Успех:** `count: 2`, на главной видны две строки, test-3 (ARCHIVED / прошлые даты) отсутствует.

---

## 6. Следующий этап (согласовано)

Автопарсинг IWWF/WSWS и маршрутизация collector — **вне текущего релиза** с обеих сторон; после стабильной приёмки seed можем синхронизировать приоритет источников в отдельном brief.

---

## 7. Документация на сайте

- `docs/COMPETITIONS_TICKER_CONTRACT_v1.md` — канон колонок и видимости
- `docs/PARSER_NEWS_COMPETITIONS_TICKER_LETTER_RU.md` — исходный brief для Parser
- Код: `app/services/competitions/`, `app/routes/competitions.py`

---

Ждём сообщение после `--seed-acceptance` — проверим API и главную в течение того же дня.

С уважением,  
**Команда Site MyWave** (mywavewake.ru)
