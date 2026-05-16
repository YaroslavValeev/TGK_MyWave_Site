# Runbook: блог + чек-лист (17.05.2026)

Выполнить **на сервере** после `git pull`. Локально уже подготовлены: `cardbg14` (иллюстрации чек-листа), отчёт по xlsx `MyWave_Parser_News (3).xlsx`.

---

## 1. Деплой кода

```bash
cd /var/www/mywave
git fetch origin main
git pull --ff-only origin main
sudo systemctl restart mywave-site
sleep 3
sudo systemctl is-active mywave-site
```

---

## 2. Чек-лист — иллюстрации в карточках (`cardbg14`)

```bash
cd /var/www/mywave
bash scripts/verify_production_frontend.sh
```

Ожидаемо: `checklist page cardbg14` — OK.

В браузере: https://mywavewake.ru/projects/checklist-org — **Ctrl+F5**.

Проверка одной картинки:

```bash
curl -sS -o /dev/null -w '%{http_code} %{size_download}\n' \
  'https://mywavewake.ru/static/images/Project/Cards/checklist/aquatory/aquatory_types_comparison.webp'
```

Ожидаемо: `200` и размер > 3000 байт.

DevTools на карточке: есть `.wake-checklist__card-art`, `data-checklist-bg="ok"`.

**Финальные иллюстрации** (когда будут): положить в  
`static/images/Project/Cards/checklist/...` или  
`static/images/Project/CheckList_Competion/cards/{id чекбокса}.webp`, затем снова `git pull` + restart.

---

## 3. Блог — диагностика Sheets (почему пусто)

### 3.1 Smoke-check live Google Sheets

```bash
cd /var/www/mywave
source venv/bin/activate
set -a && source .env && set +a

python scripts/blog_raw_feed_smoke_check.py --json | tee /tmp/blog_smoke.json
python -c "
import json,sys
d=json.load(sys.stdin)
" < /tmp/blog_smoke.json 2>/dev/null || python scripts/blog_raw_feed_smoke_check.py
```

Смотрите:

| Поле | Ожидание для «живого» блога |
|------|-----------------------------|
| `publishable_rows_count` | **≥ 20** (по xlsx-дампу от 17.05 — **24**) |
| `status_distribution` | много `PUBLISHED`, не сотни пустых `status` |
| `usable_rows_after_header` | близко к **63** (актуальный дамп), не ~344 со старым мусором |

Если `publishable_rows_count` ≈ 0–2, а в xlsx 24 — **онлайн-таблица не совпадает с файлом**. Нужно синхронизировать `raw_feed` в Google Sheets (Parser Bot / импорт), не менять код сайта.

### 3.2 API и кэш

```bash
curl -sS 'https://mywavewake.ru/api/blog/posts?limit=5' | python3 -m json.tool
curl -sS 'https://mywavewake.ru/api/blog/latest' | python3 -m json.tool
```

После синхронизации Sheets: `total` ≥ 20.

Сброс кэша (если в `.env` задан `MEDIA_UPLOAD_TOKEN`):

```bash
curl -sS -X POST 'https://mywavewake.ru/api/blog/cache/invalidate' \
  -H "Authorization: Bearer $MEDIA_UPLOAD_TOKEN"
sleep 5
curl -sS 'https://mywavewake.ru/api/blog/posts?limit=3'
```

### 3.3 Сверка PARSER_TAB / SPREADSHEET_ID

```bash
cd /var/www/mywave
grep -E '^(PARSER_TAB|PARSER_SHEET_NAME|SPREADSHEET_ID)=' .env | sed 's/=.*/=***masked***/'
```

Каноническая таблица Parser News (из правил проекта):  
`1RJpw2mAMej3a-VC6yKAsKkVQvzGStcjUC7LijNNyn50`, лист **`raw_feed`**.

`PARSER_TAB` — либо этот spreadsheet id, либо имя листа внутри `SPREADSHEET_ID`.

### 3.4 (Опционально) xlsx на сервере

Если загрузите файл как `/var/www/mywave/tmp/MyWave_Parser_News.xlsx`:

```bash
cd /var/www/mywave
source venv/bin/activate
python scripts/blog_xlsx_dry_run_importer.py \
  --xlsx /var/www/mywave/tmp/MyWave_Parser_News.xlsx \
  --sheet raw_feed \
  --out-json reports/blog_xlsx_dry_run_report.json
grep -E 'potential_publishable|total_rows' reports/blog_xlsx_dry_run_report.md 2>/dev/null || \
  python3 -c "import json; s=json.load(open('reports/blog_xlsx_dry_run_report.json')); print(s['summary'])"
```

Ожидание по дампу `(3).xlsx`: `potential_publishable: 24`, строк ~63.

---

## 4. Контент-команда (без deploy кода)

В Google Sheets `raw_feed`:

1. Строки для сайта: `status` = **`PUBLISHED`** или **`READY_TO_PUBLISH`**.
2. Заполнить **`final_posts`** (или `raw_content` / `raw_html`).
3. По возможности **`slug`** и **`cover_image_url`**.
4. Не путать с **`ARCHIVED`** (31 строка в xlsx — на сайте скрыты).

Список 24 publishable из локального анализа: `reports/blog_xlsx_publishable_list.json` в репозитории.

---

## 5. Полный smoke после деплоя

```bash
cd /var/www/mywave
bash scripts/production_smoke.sh
bash scripts/qa_mobile_precheck.sh
```

---

## Rollback

```bash
cd /var/www/mywave
git log -3 --oneline
git checkout <previous-sha>
sudo systemctl restart mywave-site
```
