# MyWave: чеклист 10/10 (сервер + репозиторий)

Пункты **1–9, 11** выполняет владелец на хосте (SSH). В репозитории закрыты: отдельный **Node-образ** с `npm ci`, **healthcheck** в compose, **дашборд** Grafana, скрипты `scripts/`.

---

## 1. systemd и права

```bash
sudo chown -R www-data:www-data /var/www/mywave
sudo chmod 600 /var/www/mywave/.env
sudo chmod +x /var/www/mywave/scripts/healthcheck.sh
sudo chmod +x /var/www/mywave/deploy/scripts/backup_mywave.sh
```

Дополнительное ужесточение `chmod` по дереву **без** затрагивания `venv/bin` оставьте на усмотрение: массовый `chmod 640` на все файлы **ломает** `gunicorn`/`python` в venv.

Убедитесь, что в `deploy/systemd/*.service` указаны `User=www-data` и `Group=www-data`, затем:

```bash
sudo systemctl daemon-reload
sudo systemctl restart mywave-site mywave-node mywave-telegram-bot
systemctl status mywave-site
```

**Критерий:** `active (running)`, нет `permission denied` в `journalctl`.

---

## 2. Gunicorn (eventlet)

- Конфиг: `gunicorn.conf.py` — `worker_class=eventlet`, `workers=1` по умолчанию.
- Docker: в `docker-compose.yml` задано `GUNICORN_WORKER_CLASS: eventlet`.

```bash
journalctl -u mywave-site -n 100 --no-pager
```

**Критерий:** нет бесконечного перезапуска воркеров, нет `Worker timeout` на каждом запросе.

---

## 3. Nginx + SSL

```bash
sudo nginx -t && sudo systemctl reload nginx
sudo certbot certificates
sudo certbot renew --dry-run
```

**Критерий:** HTTPS в браузере, в DevTools → нет критичного mixed content для основных сценариев.

---

## 4. Monitoring

| Компонент | URL / действие |
|-----------|----------------|
| Prometheus | `http://<сервер>:9090/targets` → `mywave-web` = **UP** |
| Grafana | `http://<сервер>:3000` → дашборд **MyWave — Web** — latency, RPS, uptime, exceptions |
| cAdvisor | `http://<сервер>:8088` (если поднят из compose) — CPU/RAM по контейнерам |

Провиженинг: `deploy/grafana/provisioning/`, `deploy/prometheus/prometheus.yml`.

---

## 5. Healthcheck + алерты

```bash
crontab -l
# ожидается строка вроде: */5 * * * * /var/www/mywave/scripts/healthcheck.sh
bash /var/www/mywave/scripts/healthcheck.sh
```

**Критерий:** при недоступности URL из `HEALTHCHECK_URL` приходит сообщение в Telegram (если заданы `ALERT_TELEGRAM_*` / fallback из `env.example`).

---

## 6. Backup

```bash
sudo MYWAVE_ROOT=/var/www/mywave bash /var/www/mywave/deploy/scripts/backup_mywave.sh
ls -la /var/backups/mywave/
```

Cron (пример):

`0 3 * * * MYWAVE_ROOT=/var/www/mywave /var/www/mywave/deploy/scripts/backup_mywave.sh`

---

## 7. Docker (production-образ Node)

- `Dockerfile` — веб (Gunicorn + curl для HEALTHCHECK).
- `Dockerfile.node` — `npm ci --omit=dev`, без bind-mount исходников.
- `docker compose up -d --build` → `docker compose ps` — **healthy** у `web` и `node-chat` при готовности `/health` и `node` `/health`.

---

## 8. Секреты

```bash
cd /var/www/mywave
git status
git check-ignore -v .env
bash scripts/verify_repo_secrets.sh
```

**Критерий:** `.env` в `.gitignore`; `verify_repo_secrets.sh` = 0; ротация ключей вручную в `.env` и в провайдерах (OpenAI, Telegram, admin).

---

## 9. Smoke-test и нагрузка (ручные)

1. Главная, HTTPS, чат (Socket.IO).  
2. Запись: дата, слот, Google Sheets.  
3. Google Calendar, media upload, parser / `public_url`, Telegram.  
4. Console браузера без критичных ошибок.  
5. `journalctl` / Gunicorn без лавины 500.

Нагрузка (если установлен `ab`):

```bash
ab -n 200 -c 10 https://mywavetreaning.ru/
```

**Критерий:** сервис остаётся up, `journalctl` без массового timeout.

---

## 11. Rollback (до/после релиза)

- Перед выкатом: `git tag` и бэкап (п. 6).  
- Проверка: остановка сервиса → восстановление каталога из бэкапа → `systemctl start` → `curl` `/health` **200**.

---

## 12. Критерий 10/10

- [ ] `mywave-site`, `mywave-node`, `mywave-telegram-bot` после `reboot` — active.  
- [ ] Prometheus target UP, Grafana панели обновляются.  
- [ ] Telegram-алерт по healthcheck.  
- [ ] Ежедневный backup по cron.  
- [ ] Нет секретов в git; `verify_repo_secrets.sh` чист.  
- [ ] Smoke-test пройден; нет стабильных 500.  

---

## 13. Архитектура (зафиксировано)

- Gunicorn + **eventlet**, Socket.IO стабилен.  
- Переход на **gevent** — не в этом релизе.

---

## Что «приложить» в отчёт (артефакты)

- Вывод: `systemctl status mywave-site mywave-node mywave-telegram-bot --no-pager`  
- Скрин: Prometheus → Targets, Grafana → дашборд `mywave-web`  
- Кратко: smoke-test (ok / fail по пунктам)  
- Nginx/SSL: вывод `nginx -t`, `certbot renew --dry-run`  

---

## Ссылки на файлы в репо

| Файл |
|------|
| `gunicorn.conf.py` |
| `Dockerfile`, `Dockerfile.node` |
| `docker-compose.yml` |
| `deploy/nginx/mywave.production.conf` |
| `deploy/systemd/*.service` |
| `scripts/healthcheck.sh`, `scripts/verify_repo_secrets.sh` |
| `deploy/scripts/backup_mywave.sh` |
| `deploy/prometheus/`, `deploy/grafana/provisioning/` |
| `docs/deployment/PRODUCTION_STACK.md` |
