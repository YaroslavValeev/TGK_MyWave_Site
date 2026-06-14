# Events-3 — Staging service recovery (copy-paste)

**When:** `curl http://127.0.0.1:5002/...` → `000` after `systemctl restart mywave-staging`  
**Path:** `/var/www/mywave-staging` only  
**Do NOT:** restart `mywave-site`, bot, node, prod paths

**Expected code HEAD:** `3f7e7e97` or newer (sitemap hotfix)

---

## Шаг 0 — Safety (30 сек)

```bash
# Убедитесь, что вы НЕ в prod:
pwd
# Должно быть: /var/www/mywave-staging (или root, но команды ниже — staging)

systemctl is-active mywave-site || true
# НЕ перезапускайте mywave-site
```

---

## Шаг 1 — Диагностика (скопировать вывод для Site)

```bash
export STAGING_ROOT=/var/www/mywave-staging
cd "$STAGING_ROOT"

echo "=== HEAD ==="
sudo -u www-data git rev-parse HEAD
sudo -u www-data git log -1 --oneline

echo "=== systemctl ==="
sudo systemctl status mywave-staging --no-pager -l | head -40

echo "=== journal (last 80) ==="
sudo journalctl -u mywave-staging -n 80 --no-pager

echo "=== ports ==="
ss -ltnp | grep -E '5002|5000' || echo "(nothing on 5002/5000)"

echo "=== env bind/events (no secrets) ==="
grep -E '^(GUNICORN_BIND|EVENTS_|ENABLE_GOOGLE|PUBLIC_SITE)' "$STAGING_ROOT/.env" || true
```

---

## Шаг 2 — Import smoke (без systemd)

```bash
export STAGING_ROOT=/var/www/mywave-staging
cd "$STAGING_ROOT"

sudo -u www-data bash -lc '
  cd /var/www/mywave-staging
  source venv/bin/activate
  set -a
  source .env
  set +a
  export FLASK_CONFIG=production
  export FLASK_ENV=production
  python -c "from main import app; print(\"import_ok\", len(list(app.url_map.iter_rules())))"
'
```

| Результат | Значение |
|-----------|----------|
| `import_ok <number>` | Код приложения OK → проблема в gunicorn/bind/systemd |
| Traceback | Прислать Site полный traceback |

---

## Шаг 3 — Типовые fix (по порядку)

### 3.1 Права после git pull

```bash
export STAGING_ROOT=/var/www/mywave-staging
sudo chown -R www-data:www-data "$STAGING_ROOT"
sudo chmod 640 "$STAGING_ROOT/.env" 2>/dev/null || true
```

### 3.2 GUNICORN_BIND = 5002 (staging)

```bash
export STAGING_ROOT=/var/www/mywave-staging
grep -q '^GUNICORN_BIND=' "$STAGING_ROOT/.env" \
  && sudo sed -i 's/^GUNICORN_BIND=.*/GUNICORN_BIND=127.0.0.1:5002/' "$STAGING_ROOT/.env" \
  || echo 'GUNICORN_BIND=127.0.0.1:5002' | sudo tee -a "$STAGING_ROOT/.env"

grep GUNICORN_BIND "$STAGING_ROOT/.env"
```

### 3.3 Prometheus dir (если journal: Permission denied prometheus_multiproc)

```bash
export STAGING_ROOT=/var/www/mywave-staging
sudo mkdir -p "$STAGING_ROOT/prometheus_multiproc" "$STAGING_ROOT/logs"
sudo chown -R www-data:www-data "$STAGING_ROOT/prometheus_multiproc" "$STAGING_ROOT/logs"
grep -q '^PROMETHEUS_MULTIPROC_DIR=' "$STAGING_ROOT/.env" \
  && sudo sed -i "s|^PROMETHEUS_MULTIPROC_DIR=.*|PROMETHEUS_MULTIPROC_DIR=$STAGING_ROOT/prometheus_multiproc|" "$STAGING_ROOT/.env" \
  || echo "PROMETHEUS_MULTIPROC_DIR=$STAGING_ROOT/prometheus_multiproc" | sudo tee -a "$STAGING_ROOT/.env"
```

### 3.4 Events flags (staging QA — без пробелов вокруг =)

```bash
export STAGING_ROOT=/var/www/mywave-staging
sudo nano "$STAGING_ROOT/.env"
```

Должно быть **ровно** (пример):

```text
EVENTS_API_ENABLED=1
EVENTS_PUBLIC_UI_ENABLED=1
EVENTS_REVIEW_API_ENABLED=0
EVENTS_CLASSIFIER_ENABLED=0
PUBLIC_SITE_BASE_URL=https://mywavewake.ru
ENABLE_GOOGLE_SERVICES=1
GUNICORN_BIND=127.0.0.1:5002
```

Проверка:

```bash
grep -E '^EVENTS_|^GUNICORN_BIND|^ENABLE_GOOGLE|^PUBLIC_SITE' "$STAGING_ROOT/.env"
```

### 3.5 systemd reload + restart (только staging)

```bash
sudo cp /var/www/mywave-staging/deploy/systemd/mywave-staging.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart mywave-staging
sleep 3
sudo systemctl is-active mywave-staging
```

Если `failed`:

```bash
sudo journalctl -u mywave-staging -n 50 --no-pager
```

---

## Шаг 4 — Проверка HTTP (локально на VPS)

```bash
curl -fsS -o /dev/null -w "health %{http_code}\n" http://127.0.0.1:5002/health
curl -fsS -o /dev/null -w "home %{http_code}\n" http://127.0.0.1:5002/
curl -fsS -o /dev/null -w "events %{http_code}\n" http://127.0.0.1:5002/events
curl -fsS -o /dev/null -w "sitemap %{http_code}\n" http://127.0.0.1:5002/sitemap.xml
curl -fsSI http://127.0.0.1:5002/competitions | head -5
```

**Ожидаем:** `health 200`, `home 200`, `events 200`, `sitemap 200`, `/competitions` → `302` (если flags ON).

Проверка sitemap без Jinja error:

```bash
curl -fsS http://127.0.0.1:5002/sitemap.xml | head -20
sudo journalctl -u mywave-staging -n 20 --no-pager | grep -i TemplateSyntax || echo "no template errors"
```

---

## Шаг 5 — Events QA script

```bash
export STAGING_ROOT=/var/www/mywave-staging
cd "$STAGING_ROOT"
export STAGING_BASE_URL="http://127.0.0.1:5002"
bash scripts/staging_events_qa.sh | tee /tmp/events3-staging-qa-rerun.log
echo "exit=$?"
```

Если staging доступен снаружи:

```bash
export STAGING_BASE_URL="https://staging.mywavewake.ru"
bash scripts/staging_events_qa.sh | tee -a /tmp/events3-staging-qa-rerun.log
```

---

## Шаг 6 — Если всё ещё 000 (ручной gunicorn foreground)

**Только для диагностики** — увидите ошибку в терминале:

```bash
export STAGING_ROOT=/var/www/mywave-staging
cd "$STAGING_ROOT"
sudo systemctl stop mywave-staging

sudo -u www-data bash -lc '
  cd /var/www/mywave-staging
  source venv/bin/activate
  set -a; source .env; set +a
  export GUNICORN_BIND=127.0.0.1:5002
  export FLASK_CONFIG=production
  exec gunicorn -c gunicorn.conf.py main:app
'
```

Ctrl+C после копирования ошибки, затем:

```bash
sudo systemctl start mywave-staging
```

---

## Шаг 7 — Rollback flags (если нужно вернуть YAML-only)

```bash
export STAGING_ROOT=/var/www/mywave-staging
sudo sed -i 's/^EVENTS_PUBLIC_UI_ENABLED=.*/EVENTS_PUBLIC_UI_ENABLED=0/' "$STAGING_ROOT/.env"
sudo sed -i 's/^EVENTS_API_ENABLED=.*/EVENTS_API_ENABLED=0/' "$STAGING_ROOT/.env"
sudo systemctl restart mywave-staging
curl -fsS -o /dev/null -w "events %{http_code}\n" http://127.0.0.1:5002/events
```

---

## Шаг 8 — Что прислать Site

```text
git rev-parse HEAD:
systemctl is-active:
health/sitemap/events HTTP codes:
staging_events_qa.sh summary (PASS/FAIL counts):
import smoke: ok / traceback:
First error line from journal (if any):
Production touched: no
```

---

## Связанные документы

- `EVENTS_PR3_STAGING_OWNER_RUNBOOK.md`
- `BOOKING_PHASE2_STAGING_BOOTSTRAP_RUNBOOK.md` §2, §5
