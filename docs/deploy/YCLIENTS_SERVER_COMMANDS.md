# YCLIENTS — точные команды для сервера

Сервер: `62.113.42.227` · cwd: `/var/www/mywave` · сервис: `mywave-site`  
**Не трогать:** `mywave-node`, `mywave-telegram-bot`, TGbotAdmin (пока нет GO).

---

## A. Owner вручную (до кода) — обязательно

### A1. Личный кабинет разработчика YCLIENTS

1. Зарегистрировать / войти: https://clck.ru/3REPzB  
   Гайд: https://support.yclients.com/67-68-189--poshagovyj-gajd-po-razmesheniyu-v-marketplejse/
2. Взять **Токен партнера** (Настройки аккаунта).
3. Подключить приложение к филиалу `2043174`  
   - публичное: Marketplace  
   - непубличное: https://support.yclients.com/67-68-202--kak-prodolzhit-polzovatsya-svoej-integraciej-posle-skrytiya-razdela-webhook/
4. User token: вкладка приложения «Доступ к API»  
   **или** получить через `POST /auth` (команда B3 ниже).

### A2. График катера в YCLIENTS (до 30.09.2026)

- Понедельник — выходной  
- Четверг — перерыв 16:00–20:00  

### A3. (Рекомендуется) доп. поля записи

В ЛК создать custom fields, например:

- `mw_source` (text)  
- `mw_internal_id` (text)

---

## B. Установка токенов в `.env` (после merge ветки)

```bash
set -euo pipefail
cd /var/www/mywave
TS=$(date +%Y%m%d_%H%M%S)
sudo cp -a .env ".env.bak_yclients_${TS}"

# Подставьте реальные значения (НЕ коммитьте):
PARTNER_TOKEN='PASTE_PARTNER_TOKEN'
USER_TOKEN='PASTE_USER_TOKEN'          # или получите через B3
WEBHOOK_SECRET="$(openssl rand -hex 24)"
GATEWAY_SECRET="$(openssl rand -hex 24)"

python3 - <<PY
from pathlib import Path
path = Path(".env")
updates = {
    "YCLIENTS_ENABLED": "0",
    "YCLIENTS_READ_ONLY_ENABLED": "1",
    "YCLIENTS_WRITE_ENABLED": "0",
    "YCLIENTS_COMPANY_ID": "2043174",
    "YCLIENTS_API_BASE_URL": "https://api.yclients.com/api/v1",
    "YCLIENTS_PARTNER_TOKEN": """$PARTNER_TOKEN""",
    "YCLIENTS_USER_TOKEN": """$USER_TOKEN""",
    "YCLIENTS_WEBHOOK_SECRET": """$WEBHOOK_SECRET""",
    "YCLIENTS_GATEWAY_SECRET": """$GATEWAY_SECRET""",
    "BOAT_PROVIDER": "yclients",
    "BOAT_SLOT_DURATION_MINUTES": "30",
    "BOAT_CAPACITY": "1",
    "YCLIENTS_WIDGET_URL": "https://n347190.yclients.com/company/2043174/personal/menu?o=",
}
# NOTE: run the shell version below if heredoc quoting is awkward
print("use shell updater")
PY

# Надёжный updater:
python3 <<'PY'
from pathlib import Path
import os
path = Path(".env")
updates = {
    "YCLIENTS_ENABLED": "0",
    "YCLIENTS_READ_ONLY_ENABLED": "1",
    "YCLIENTS_WRITE_ENABLED": "0",
    "YCLIENTS_COMPANY_ID": "2043174",
    "YCLIENTS_API_BASE_URL": "https://api.yclients.com/api/v1",
    "YCLIENTS_PARTNER_TOKEN": os.environ["PARTNER_TOKEN"],
    "YCLIENTS_USER_TOKEN": os.environ["USER_TOKEN"],
    "YCLIENTS_WEBHOOK_SECRET": os.environ["WEBHOOK_SECRET"],
    "YCLIENTS_GATEWAY_SECRET": os.environ["GATEWAY_SECRET"],
    "BOAT_PROVIDER": "yclients",
    "BOAT_SLOT_DURATION_MINUTES": "30",
    "BOAT_CAPACITY": "1",
}
lines = path.read_text(encoding="utf-8").splitlines()
seen=set(); out=[]
for line in lines:
    s=line.strip()
    if s and not s.startswith("#") and "=" in line:
        k=line.split("=",1)[0].strip()
        if k in updates:
            out.append(f"{k}={updates[k]}"); seen.add(k); continue
    out.append(line)
for k,v in updates.items():
    if k not in seen:
        out.append(f"{k}={v}")
path.write_text("\n".join(out)+"\n", encoding="utf-8")
print("webhook_secret_set", bool(os.environ["WEBHOOK_SECRET"]))
print("gateway_secret_set", bool(os.environ["GATEWAY_SECRET"]))
PY

sudo chown www-data:www-data .env
sudo chmod 600 .env
echo "WEBHOOK_URL=https://mywavewake.ru/public/integrations/yclients/webhook?token=${WEBHOOK_SECRET}"
echo "GATEWAY_SECRET=${GATEWAY_SECRET}"
```

Перед блоком updater обязательно:

```bash
export PARTNER_TOKEN USER_TOKEN WEBHOOK_SECRET GATEWAY_SECRET
```

### B3. Получить User token через API (если нет в ЛК)

```bash
cd /var/www/mywave
source venv/bin/activate
set -a; source .env; set +a
export YCLIENTS_USER_PASSWORD='ПАРОЛЬ_ПОЛЬЗОВАТЕЛЯ_YCLIENTS'
python scripts/yclients_auth_user_token.py --login 'EMAIL_ИЛИ_ЛОГИН_YCLIENTS'
# Скопировать напечатанный токен в .env → YCLIENTS_USER_TOKEN=
unset YCLIENTS_USER_PASSWORD
```

---

## C. Deploy кода (после Owner GO на merge)

```bash
set -euo pipefail
PROD_ROOT=/var/www/mywave
GIT="git -c safe.directory=${PROD_ROOT}"
cd "$PROD_ROOT"
TS=$(date +%Y%m%d_%H%M%S)

# backup
if [ -x deploy/scripts/backup_mywave.sh ]; then
  sudo deploy/scripts/backup_mywave.sh
else
  sudo tar --exclude='./venv' --exclude='./.git' -czf "/root/mywave_before_yclients_${TS}.tar.gz" .
fi

# подставьте ветку/SHA после merge
$GIT fetch origin
$GIT checkout feat/yclients-api-s5-contract   # или main после merge
# $GIT pull --ff-only

source venv/bin/activate
pytest \
  tests/unit/test_yclients_provider.py \
  tests/integration/test_yclients_webhook.py \
  -q

sudo systemctl restart mywave-site
sleep 5
systemctl is-active mywave-site
curl -fsS https://mywavewake.ru/health/live
```

---

## D. S5 read-only smoke (токены уже в `.env`)

```bash
cd /var/www/mywave
source venv/bin/activate
set -a; source .env; set +a

# временно для smoke (не оставляйте WRITE=1)
export YCLIENTS_ENABLED=1
export YCLIENTS_READ_ONLY_ENABLED=1
export YCLIENTS_WRITE_ENABLED=0

python scripts/yclients_discover.py | tee /tmp/yclients_discover.json
# Из вывода возьмите:
#   YCLIENTS_STAFF_ID=...
#   YCLIENTS_SERVICE_IDS=...
# и допишите в .env, затем:

python scripts/yclients_smoke_read.py --date "$(date -d '+1 day' +%F)"
```

После успешного discover — зафиксировать ID в `.env` и перезапустить:

```bash
# отредактировать .env: YCLIENTS_STAFF_ID / YCLIENTS_SERVICE_IDS
# затем для prod-smoke с ENABLED=1 (READ only):
sudo sed -i 's/^YCLIENTS_ENABLED=.*/YCLIENTS_ENABLED=1/' .env
sudo sed -i 's/^YCLIENTS_WRITE_ENABLED=.*/YCLIENTS_WRITE_ENABLED=0/' .env
sudo chown www-data:www-data .env
sudo systemctl restart mywave-site
```

---

## E. Webhook в ЛК YCLIENTS

URL (секрет из `.env`):

```text
https://mywavewake.ru/public/integrations/yclients/webhook?token=<YCLIENTS_WEBHOOK_SECRET>
```

События: записи create/update/delete.

Проверка с сервера:

```bash
SECRET=$(grep '^YCLIENTS_WEBHOOK_SECRET=' /var/www/mywave/.env | cut -d= -f2-)
curl -sS -X POST \
  "https://mywavewake.ru/public/integrations/yclients/webhook?token=${SECRET}" \
  -H 'Content-Type: application/json' \
  -d '{"company_id":2043174,"resource":"record","resource_id":1,"status":"create","data":{"id":1,"attendance":0}}'
```

Ожидание: `{"ok":true,...}` при `YCLIENTS_ENABLED=1`.

---

## F. Internal gateway (Site / Bot)

```bash
GW=$(grep '^YCLIENTS_GATEWAY_SECRET=' /var/www/mywave/.env | cut -d= -f2-)

curl -sS "https://mywavewake.ru/api/internal/yclients/health" \
  -H "X-MyWave-Gateway-Secret: ${GW}"

curl -sS "https://mywavewake.ru/api/internal/yclients/slots?date=$(date -d '+1 day' +%F)" \
  -H "X-MyWave-Gateway-Secret: ${GW}"
```

Создание записи — **только** после `YCLIENTS_WRITE_ENABLED=1` + Owner GO:

```bash
curl -sS -X POST "https://mywavewake.ru/api/internal/yclients/bookings" \
  -H "X-MyWave-Gateway-Secret: ${GW}" \
  -H 'Content-Type: application/json' \
  -d '{
    "date":"2026-07-29",
    "time":"10:00",
    "client_name":"Тест",
    "client_phone":"79160000000",
    "set_count":1,
    "source":"site",
    "internal_id":"smoke-1"
  }'
```

---

## G. Cron reconcile (после S5)

```bash
sudo tee /etc/cron.d/mywave-yclients-sync >/dev/null <<'EOF'
*/15 * * * * www-data cd /var/www/mywave && ./venv/bin/python scripts/sync_yclients_bookings.py --days-back 1 --days-forward 14 >> /var/log/mywave-yclients-sync.log 2>&1
EOF
sudo chmod 644 /etc/cron.d/mywave-yclients-sync
```

Пока mirror stub — cron в dry-run безопасен; `--apply` включать после реализации Calendar upsert.

---

## H. Rollback

```bash
cd /var/www/mywave
# 1) выключить флаги
sudo sed -i 's/^YCLIENTS_ENABLED=.*/YCLIENTS_ENABLED=0/' .env
sudo sed -i 's/^YCLIENTS_WRITE_ENABLED=.*/YCLIENTS_WRITE_ENABLED=0/' .env
sudo systemctl restart mywave-site

# 2) при необходимости откат кода
# git -c safe.directory=/var/www/mywave checkout <PREV_HEAD>
# sudo systemctl restart mywave-site
curl -fsS https://mywavewake.ru/health/live
```

---

## Acceptance checklist

- [ ] Partner + User token работают (`discover` + `smoke_read`)
- [ ] STAFF_ID / SERVICE_IDS записаны
- [ ] Webhook URL с token в ЛК
- [ ] `YCLIENTS_WRITE_ENABLED=0` до Owner GO
- [ ] Boat widget остаётся fallback для клиентов
- [ ] Gym не затронут
