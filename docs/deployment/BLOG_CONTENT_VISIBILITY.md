# Blog: почему на сайте пусто при наличии данных в Sheets

**Backend routing стабилен — не менять.** Этот документ для ops/content и диагностики pipeline.

## Как сайт решает, что показывать

Источник: `raw_feed` в Google Sheets → [`app/services/blog/store.py`](../../app/services/blog/store.py).

Строка попадает на витрину только если [`is_publishable_row`](../../app/services/blog/publishability.py):

| Условие | Требование |
|---------|------------|
| `status` | `READY_TO_PUBLISH` или `PUBLISHED` (регистр не важен) |
| Не | `ARCHIVED`, `DRAFT`, `APPROVED` alone |
| Контент | Есть `final_posts` / `text` / `raw_content` / `raw_html` |
| `slug` | Заполнен и валиден после маппинга |

**Важно:** `APPROVED` без перехода в `READY_TO_PUBLISH` на сайте **не отображается** — это контракт v1, не баг routing.

## Быстрая диагностика на сервере

```bash
cd /var/www/mywave
source venv/bin/activate
export $(grep -v '^#' .env | xargs)  # осторожно: только на сервере

python scripts/blog_raw_feed_smoke_check.py
```

Смотрите в отчёте:

- сколько строк `READY_TO_PUBLISH` / `PUBLISHED`
- сколько `APPROVED` с контентом, но не publishable
- сколько без `slug`

## API / страницы (без изменения кода)

| URL | Назначение |
|-----|------------|
| `GET /blog` | HTML список |
| `GET /blog/<slug>` | Страница поста |
| `GET /api/blog/posts` | JSON список |
| `?db_only=1` | Только SQLite fallback (без Sheets) |

```bash
curl -sS "https://mywavewake.ru/api/blog/posts?limit=5" | python3 -m json.tool
curl -sS "https://mywavewake.ru/api/blog/posts?limit=5&db_only=1" | python3 -m json.tool
```

Если `db_only=1` даёт посты, а без него — пусто: проблема в **статусах/маппинге Sheets**, не в шаблоне.

## Две разные таблицы (частая путаница)

| Таблица | ID (пример) | Лист блога |
|---------|-------------|------------|
| **MyWave_Parser_News** (источник блога) | `1RJpw2mAMej3a-VC6yKAsKkVQvzGStcjUC7LijNNyn50` | `raw_feed` |
| **MyWave_Admin_Tg_Bot** (бронь, клиенты, каталог) | `1kyNQVjeLLe4Ra6oWuf84fHqSjUlWXI8MakVMOrCgic0` | **нет** `raw_feed`; `Catalog_Posts` — не витрина блога |

Файл `MyWave_Admin_Tg_Bot.xlsx` **не содержит** постов блога. Нужен экспорт **Parser News** (`raw_feed`) или синхронизация Parser Bot в онлайн-таблицу.

Быстрый импорт на сервере из XLSX Parser News (fallback в SQLite):

```bash
flask migrate-blog   # один раз, если старая схема blog_post
python scripts/blog_xlsx_import_to_db.py --xlsx /path/MyWave_Parser_News.xlsx --sheet raw_feed
```

Диагностика без секретов: `GET /api/blog/diagnostics`

## Типичные причины empty state

1. **Статус в таблице** — Parser оставил `APPROVED` / `DRAFT`, не `READY_TO_PUBLISH`.
2. **Пустой slug** — не сгенерирован при ingest.
3. **Кэш Sheets** — TTL ~60–180 с; после публикации в таблице подождать или:
   ```bash
   curl -X POST https://mywavewake.ru/api/blog/cache/invalidate \
     -H "Authorization: Bearer $MEDIA_UPLOAD_TOKEN"
   ```
4. **Sync в SQLite не запускался** — витрина читает Sheets first; БД — fallback. Cron sync см. `app/cli/blog_sync.py` / runbook.
5. **Неверный SPREADSHEET_ID** — на prod `SPREADSHEET_ID` часто указывает на **Admin/Tg Bot**; блог должен читать **Parser News** через отдельную переменную:

```bash
# /var/www/mywave/.env
PARSER_NEWS_SPREADSHEET_ID=1RJpw2mAMej3a-VC6yKAsKkVQvzGStcjUC7LijNNyn50
PARSER_SHEET_NAME=raw_feed
# SPREADSHEET_ID=...  # оставить для брони/бота, не подменять на Parser News
```

После правки: `sudo systemctl restart mywave-site`, затем `GET /api/blog/diagnostics` — `spreadsheet_id_tail` должен заканчиваться на `NNyn50`, не на `OrCgic0` / `M0Rcglc8`.

## Действия для контент-команды (без deploy)

1. В `raw_feed` выставить `status=READY_TO_PUBLISH` или `PUBLISHED` для готовых строк.
2. Заполнить `slug`, `final_posts` или `content_md`.
3. Дождаться TTL кэша или invalidate cache.
4. Проверить `curl -I https://mywavewake.ru/blog` → 200 и превью на главной.

## Что НЕ делать

- Не менять `blog_bp` routes без отдельного issue.
- Не ослаблять `publishability` на prod без согласования контракта Parser ↔ Site.
- Не коммитить `service_account.json`.
