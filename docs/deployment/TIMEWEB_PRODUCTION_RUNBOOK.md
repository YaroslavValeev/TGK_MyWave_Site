# Timeweb Production Runbook

## Контур

- Проект Timeweb: `Site_MyWaveTraining`
- Сервер: `mywave-bot-server`
- IPv4: `62.113.42.227`
- IPv6: `2a03:6f00:a::5178`
- ОС: `Ubuntu 22.04`
- Canonical домен: `mywavewake.ru`
- `www.mywavewake.ru` должен редиректить на `https://mywavewake.ru`

## Release preflight

В репозитории:

```bash
bash scripts/release_preflight.sh 894310a7120ff58ae44b7135afae478af88e6488
```

Ручной эквивалент:

```bash
git rev-parse HEAD
git status --short
git log --oneline -5
```

Критерий:

- `git status --short` пустой
- `HEAD` совпадает с согласованным release commit
- в релиз не попадают локальные незакоммиченные изменения

## Обязательные systemd services

- `mywave-site.service` — Flask + Gunicorn + eventlet на `127.0.0.1:5000`
- `mywave-node.service` — optional compatibility proxy на `127.0.0.1:5001`
- `mywave-telegram-bot.service` — отдельный control bot (`telegram_bot.py` -> `automation/tg_control_bot.py`)

Примечание:

- отдельного второго production bot service сейчас не требуется;
- Telegram webhook/runtime сайта работает внутри Flask-приложения;
- `mywave-node.service` держим включённым только если нужен путь `/node-chat/*`.

## Env variables

Заполняются только на сервере в `/var/www/mywave/.env`.

Обязательные:

- `SECRET_KEY`
- `FLASK_ENV`
- `FLASK_CONFIG`
- `DATABASE_URL`
- `DOMAIN`
- `BASE_URL`
- `PUBLIC_BASE_URL`
- `SITE_BASE_URL`
- `SERVER_NAME`
- `HEALTHCHECK_URL`
- `OPENAI_API_KEY`
- `GPTS_MODEL`
- `FALLBACK_MODEL`
- `SPREADSHEET_ID`
- `GOOGLE_CALENDAR_ID`
- `GOOGLE_SERVICE_ACCOUNT_FILE`
- `MEDIA_UPLOAD_TOKEN`

Telegram / alerts:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `NOTIFICATION_BOT_TOKEN`
- `TRAINER_CHAT_ID`
- `TG_CONTROL_BOT_TOKEN`
- `TG_CONTROL_ALLOWED_IDS`
- `ALERT_TELEGRAM_BOT_TOKEN`
- `ALERT_TELEGRAM_CHAT_ID`
- `WEBHOOK_URL`

Runtime / optional:

- `GUNICORN_BIND`
- `GUNICORN_WORKERS`
- `GUNICORN_WORKER_CLASS`
- `GUNICORN_TIMEOUT`
- `GUNICORN_GRACEFUL_TIMEOUT`
- `RATELIMIT_STORAGE_URI`
- `SOCKETIO_MESSAGE_QUEUE`
- `REDIS_URL`
- `SENTRY_DSN`
- `ENABLE_AI_HEALTH_CHECK`
- `PROMETHEUS_MULTIPROC_DIR`
- `MW_REPO_PATH`

Критично:

- `OPENAI_API_KEY` содержит только API key
- `GPTS_MODEL` / `FALLBACK_MODEL` содержат только имена моделей
- `.env` и `service_account.json` не хранятся в Git

## Deploy commands

На сервере:

```bash
cd /var/www/mywave
git fetch --all --tags
git checkout main
git pull --ff-only origin main
bash scripts/release_preflight.sh
/var/www/mywave/venv/bin/pip install -r requirements.txt
/var/www/mywave/venv/bin/flask db upgrade
sudo cp deploy/systemd/mywave-site.service /etc/systemd/system/mywave-site.service
sudo cp deploy/systemd/mywave-node.service /etc/systemd/system/mywave-node.service
sudo cp deploy/systemd/mywave-telegram-bot.service /etc/systemd/system/mywave-telegram-bot.service
sudo cp deploy/nginx/mywave.production.conf /etc/nginx/sites-available/mywave
sudo ln -sfn /etc/nginx/sites-available/mywave /etc/nginx/sites-enabled/mywave
sudo nginx -t
sudo systemctl daemon-reload
sudo systemctl enable mywave-site mywave-telegram-bot
sudo systemctl enable mywave-node
sudo systemctl restart mywave-site mywave-node mywave-telegram-bot
sudo systemctl reload nginx
sudo certbot --nginx -d mywavewake.ru -d www.mywavewake.ru
```

Если `node-chat` не нужен:

```bash
sudo systemctl disable --now mywave-node
```

## Backup / rollback

Перед выкатом:

```bash
sudo MYWAVE_ROOT=/var/www/mywave bash /var/www/mywave/deploy/scripts/backup_mywave.sh
```

Daily cron:

```bash
0 3 * * * MYWAVE_ROOT=/var/www/mywave /var/www/mywave/deploy/scripts/backup_mywave.sh
*/5 * * * * MYWAVE_ROOT=/var/www/mywave /var/www/mywave/scripts/healthcheck.sh >> /var/log/mywave/healthcheck.log 2>&1
```

Rollback checklist:

1. `cd /var/www/mywave`
2. `sudo systemctl stop mywave-site mywave-node mywave-telegram-bot`
3. восстановить каталог из последнего backup
4. вернуть прежние `deploy/systemd/*.service` и `/etc/nginx/sites-available/mywave`, если они менялись
5. `sudo systemctl daemon-reload`
6. `sudo nginx -t && sudo systemctl reload nginx`
7. `sudo systemctl start mywave-site mywave-node mywave-telegram-bot`
8. проверить `curl -fsS https://mywavewake.ru/health`

Целевое время rollback: 2–5 минут.

## Smoke-test checklist

1. `https://mywavewake.ru` открывается.
2. `https://www.mywavewake.ru` редиректит на `https://mywavewake.ru`.
3. SSL активен, `certbot renew --dry-run` проходит.
4. `/health` возвращает `200`.
5. `/metrics` отдаёт метрики.
6. `https://mywavewake.ru/node-chat/health` отвечает, если Node включён.
7. Чат открывается на сайте.
8. Socket.IO не даёт ошибок подключения и reconnect spam.
9. Запись на тренировку проходит.
10. Google Sheets обновляется.
11. Google Calendar создаёт событие без дублей.
12. Telegram-уведомление приходит.
13. Media upload возвращает `public_url`, `url`, `cover_image_url`, `image_url` на `https://mywavewake.ru/...`.
14. Parser получает корректные публичные URL.
15. В логах нет `500`, `Traceback`, `Permission denied`, `Worker timeout`, repeated restart.
16. После reboot сервисы поднимаются автоматически.

## Known limitations

- Без Redis production-режим остаётся на `workers=1`; это ожидаемо для Socket.IO + eventlet.
- `mywave-node.service` — optional compatibility слой, а не канонический runtime для основного веб-чата.
- Extended monitoring (`Prometheus`, `Grafana`, `cAdvisor`) держим выключенным по умолчанию на сервере 2 CPU / 4 GB RAM и включаем только по необходимости.
