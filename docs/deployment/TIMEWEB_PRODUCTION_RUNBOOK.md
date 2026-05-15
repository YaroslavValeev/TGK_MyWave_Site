# Timeweb Production Runbook

## Контур

- Проект Timeweb: `Site_MyWaveTraining`
- Сервер: `mywave-bot-server`
- IPv4: `62.113.42.227`
- IPv6: `2a03:6f00:a::5178`
- ОС: `Ubuntu 22.04`
- Canonical домен: `mywavewake.ru`
- `www.mywavewake.ru` должен редиректить на `https://mywavewake.ru`

## Production runtime baseline (заморожен)

| Baseline | Commit | Статус |
|----------|--------|--------|
| Runtime (frozen) | `3de56f8c` | FROZEN |
| Frontend/docs | `48dc9c64` | ACTIVE |
| QA/Ops governance | `0a2a0e1a` | ACTIVE |

**Production:** https://mywavewake.ru · Timeweb Cloud · Ubuntu 22.04 · 2 CPU / 4 GB / 50 GB NVMe

Не менять runtime без issue + rollback + smoke.  
Фаза: **Production Stabilization + QA Discipline** — [STABILIZATION_QA_PHASE.md](STABILIZATION_QA_PHASE.md).

| Gate / QA | Документ |
|-----------|----------|
| Release gate | [RELEASE_GATE_CHECKLIST.md](RELEASE_GATE_CHECKLIST.md) |
| Mobile QA | [MOBILE_QA_MATRIX.md](../qa/MOBILE_QA_MATRIX.md) |
| Incidents | [PRODUCTION_INCIDENT_POLICY.md](../ops/PRODUCTION_INCIDENT_POLICY.md) |
| UX scope | [FRONTEND_POLISH_PHASE.md](FRONTEND_POLISH_PHASE.md) |

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

## Google Service Account

См. [GOOGLE_SERVICE_ACCOUNT_SETUP.md](GOOGLE_SERVICE_ACCOUNT_SETUP.md).

Кратко: положить JSON в `/var/www/mywave/instance/service_account.json`, `chmod 600`, выдать SA доступ к Sheet/Calendar/Drive.

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

## Redis (production)

```bash
sudo apt install -y redis-server
sudo systemctl enable redis-server
```

В `.env`:

```env
REDIS_URL=redis://127.0.0.1:6379/0
RATELIMIT_STORAGE_URI=redis://127.0.0.1:6379/0
SOCKETIO_MESSAGE_QUEUE=redis://127.0.0.1:6379/0
```

## Booking API (канонический endpoint)

```text
GET /api/calendar/slots/<YYYY-MM-DD>?service=boat|gym|camp|...
```

Пути `/api/calendar/available_slots/` и `/api/available_slots/` **не используются**.

## Health endpoints

| URL | Назначение |
|-----|------------|
| `/health/live` | liveness, всегда `200` |
| `/health/ready` | readiness, `503` только если БД недоступна |
| `/health` | `ok` / `degraded` (`200`) / `unhealthy` (`503`) |

Optional (Redis, Sentry, Google SA file) дают `degraded`, но не `503`.

Проверка зависимостей перед деплоем:

```bash
bash scripts/import_preflight.sh
```

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
4. `/health` возвращает `200` (`ok` или `degraded`).
5. `/blog` возвращает `200` (даже без постов).
6. `GET /api/calendar/slots/<date>?service=boat` возвращает `200` (массив, может быть пустым).
7. `/metrics` отдаёт метрики.
8. `https://mywavewake.ru/node-chat/health` отвечает, если Node включён.
9. Чат открывается на сайте.
10. Socket.IO не даёт ошибок подключения и reconnect spam.
11. Запись на тренировку проходит.
12. Google Sheets обновляется.
13. Google Calendar создаёт событие без дублей.
14. Telegram-уведомление приходит.
15. Media upload возвращает `public_url`, `url`, `cover_image_url`, `image_url` на `https://mywavewake.ru/...`.
16. Parser получает корректные публичные URL.
17. Фото отзывов и иллюстрации чек-листа без 404 в Network.
18. В логах нет `500`, `Traceback`, `Permission denied`, `Worker timeout`, repeated restart.
19. После reboot сервисы поднимаются автоматически.

## Known limitations

- Без Redis production-режим остаётся на `workers=1`; это ожидаемо для Socket.IO + eventlet.
- `mywave-node.service` — optional compatibility слой, а не канонический runtime для основного веб-чата.
- Extended monitoring (`Prometheus`, `Grafana`, `cAdvisor`) держим выключенным по умолчанию на сервере 2 CPU / 4 GB RAM и включаем только по необходимости.
