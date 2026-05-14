# MyWaveWake: production-стек (Timeweb)

Финальный чеклист 10/10: **[PRODUCTION_10_CHECKLIST.md](PRODUCTION_10_CHECKLIST.md)**.
Пошаговый runbook для владельца: **[TIMEWEB_PRODUCTION_RUNBOOK.md](TIMEWEB_PRODUCTION_RUNBOOK.md)**.

## Worker Socket.IO + Gunicorn

- Во всём приложении Socket.IO и monkey-patch идут через **eventlet** (`app.extensions.socketio`, `main.py`).
- Соответствующий воркер Gunicorn: **`eventlet`**, не `sync`. Один воркер (`GUNICORN_WORKERS=1`) — базовая рекомендация для in-memory Engine.IO.
- **GeventWebSocketWorker** не используется без миграции `async_mode` и патча на **gevent**; это отдельное согласованное изменение.
- Масштабирование воркеров: задать **Redis** и переменную **`SOCKETIO_MESSAGE_QUEUE=redis://...`** (см. `.env.example`).

## Запуск

- **Produсtion (сервер):**  
  `gunicorn -c gunicorn.conf.py main:app`  
- **Локально (dev):**  
  `python main.py` (порт 5000–5010, как раньше).
- **Flask-конфиг:** `FLASK_ENV=production`, `FLASK_CONFIG=production` — см. `main.py` → `config.ProductionConfig`.
- **Bind:** `127.0.0.1:5000` за Nginx.
- **Рекомендуемая БД на сервере:** `DATABASE_URL=sqlite:////var/www/mywave/instance/mywave.db`.

## Production URLs

- Canonical домен: `https://mywavewake.ru`
- Дополнительный домен: `https://www.mywavewake.ru` → 301 на основной
- Healthcheck: `https://mywavewake.ru/health`
- Media/public URLs: `SITE_BASE_URL=https://mywavewake.ru`
- Blog canonical URLs: `https://mywavewake.ru/blog/{slug}`

## Файлы (ориентиры)

| Назначение | Путь |
|------------|------|
| Gunicorn | `gunicorn.conf.py` |
| WSGI-алиас | `wsgi.py` → `import main; application` |
| Nginx (хост) | `deploy/nginx/mywave.production.conf` |
| Nginx (Docker) | `deploy/nginx/docker.conf` |
| systemd | `deploy/systemd/*.service` |
| Docker | `Dockerfile`, `docker-compose.yml` |
| Prometheus | `deploy/prometheus/prometheus.yml` |
| Grafana | `deploy/grafana/provisioning/**` |
| Health/cron | `scripts/healthcheck.sh` |
| Backup | `deploy/scripts/backup_mywave.sh` |
| Пример env | `.env.example` → скопировать в `.env` (не в Git) |

## Метрики

- HTTP: `prometheus_flask_exporter` (без дублирующего auto-`/metrics`), отдача **одним** маршрутом `app/routes/metrics_api.py` → **`/metrics`**.
- Внутренняя логика: `app/services/prometheus_metrics.py` (в т.ч. `mywave_uptime_seconds`).

## Node compatibility (порт 5001)

- `server.js` использует **встроенный `fetch` (Node 18+)**.
- Node-сервис не является каноническим runtime для основного веб-чата; основной chat/API живёт во Flask.
- `mywave-node.service` можно держать включённым только если реально нужен `/node-chat/*`.

## Безопасность

- Секреты только в `.env` на сервере; `chmod 600 .env`.
- `GOOGLE_SERVICE_ACCOUNT_FILE` должен указывать на серверный файл вне Git, например `/var/www/mywave/instance/service_account.json`.
- См. `.gitignore` / `.dockerignore`: исключены `.env`, `service_account.json`, SQLite DB и диагностические артефакты.
