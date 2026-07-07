# Online Coaching Phase 2 — команды для сервера (Owner)

**Сервис:** только `mywave-site`  
**Не трогать:** `mywave-node`, TGbotAdmin, `mywave-telegram-bot`  
**Код:** PR #90+ (ветка `feat/online-coaching-phase2` или `main` после merge)

---

## 0. Базовый деплой Phase 2 (один раз)

```bash
set -euo pipefail
PROD_ROOT=/var/www/mywave
cd "$PROD_ROOT"
PY="$PROD_ROOT/venv/bin/python"
SERVICE_USER="${SERVICE_USER:-www-data}"

# После merge PR #91 + #94 (2026-07-07):
EXPECTED_HEAD="7b4589d229f795db4103712843ab0c0090915b61"

git -c safe.directory="$PROD_ROOT" fetch origin main
git -c safe.directory="$PROD_ROOT" checkout main
git -c safe.directory="$PROD_ROOT" pull --ff-only origin main
test "$(git -c safe.directory="$PROD_ROOT" rev-parse HEAD)" = "$EXPECTED_HEAD"

sudo mkdir -p "$PROD_ROOT/logs" "$PROD_ROOT/instance"
sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$PROD_ROOT/logs" "$PROD_ROOT/instance"

source venv/bin/activate
pip install -r requirements.txt

DISABLE_TELEGRAM=1 ENABLE_GOOGLE_SERVICES=0 ONLINE_COACHING_ENABLED=1 \
  "$PY" scripts/smoke_online_coaching_routes.py

DISABLE_TELEGRAM=1 ENABLE_GOOGLE_SERVICES=0 ONLINE_COACHING_ENABLED=1 \
  "$PY" -m pytest tests/unit/test_online_coaching_phase2.py tests/unit/test_online_coaching_*.py -q

sudo systemctl restart mywave-site
sleep 12
curl -sf https://mywavewake.ru/health/live
```

---

## 1. Reminders (cron) — PR-модуль A

### .env

```bash
sudo nano /var/www/mywave/.env
```

Добавить:

```env
ONLINE_COACHING_REMINDERS_ENABLED=1
```

### Dry-run

```bash
cd /var/www/mywave
source venv/bin/activate
set -a && source .env && set +a
ONLINE_COACHING_ENABLED=1 ONLINE_COACHING_REMINDERS_ENABLED=1 \
  python scripts/run_online_coaching_reminders.py --dry-run
```

Ожидание: `due=N processed=N` (или `due=0` если нет просроченных).

### Cron (каждый час)

```bash
sudo crontab -u www-data -e
```

Строка:

```cron
0 * * * * cd /var/www/mywave && set -a && . ./.env && set +a && ONLINE_COACHING_ENABLED=1 ONLINE_COACHING_REMINDERS_ENABLED=1 ./venv/bin/python scripts/run_online_coaching_reminders.py >> logs/oc_reminders.log 2>&1
```

### Проверка лога

```bash
tail -30 /var/www/mywave/logs/oc_reminders.log
```

---

## 2. T-Bank API — PR-модуль B

### .env

```env
ONLINE_COACHING_TBANK_API_ENABLED=1
TBANK_TERMINAL_KEY=ВАШ_TERMINAL_KEY
TBANK_SECRET_KEY=ВАШ_SECRET_KEY
TBANK_API_URL=https://securepay.tinkoff.ru/v2
TBANK_NOTIFICATION_URL=https://mywavewake.ru/api/online-coaching/tbank/webhook
```

### Перезапуск

```bash
sudo systemctl restart mywave-site
sleep 12
curl -sf https://mywavewake.ru/health/live
```

### В кабинете T-Bank

- Notification URL: `https://mywavewake.ru/api/online-coaching/tbank/webhook`
- Метод: POST

### Smoke (без реальной оплаты)

```bash
curl -sI -X POST https://mywavewake.ru/api/online-coaching/tbank/webhook \
  -H "Content-Type: application/json" \
  -d '{}' | head -5
```

Ожидание: `403` (invalid token) — маршрут жив, CSRF не блокирует.

### Admin UI

1. `/admin/online-coaching/<id>`
2. Кнопка **«Создать ссылку T-Bank (API)»**
3. После оплаты клиентом — webhook → статус `paid` автоматически

---

## 3. Telegram video upload — PR-модуль C

Используется **NOTIFICATION_BOT** (тот же, что для заявок тренеру).  
**Не** перенастраивать `mywave-telegram-bot`.

### .env

```env
ONLINE_COACHING_TELEGRAM_VIDEO_UPLOAD_ENABLED=1
ONLINE_COACHING_APPLICATIONS_ENABLED=1
TELEGRAM_WEBHOOK_SECRET=СГЕНЕРИРУЙТЕ_СЛУЧАЙНУЮ_СТРОКУ_32+
NOTIFICATION_BOT_TOKEN=уже_должен_быть
```

### Установка webhook (замените TOKEN и SECRET)

```bash
BOT_TOKEN="$(grep -E '^NOTIFICATION_BOT_TOKEN=' /var/www/mywave/.env | cut -d= -f2-)"
WEBHOOK_SECRET="$(grep -E '^TELEGRAM_WEBHOOK_SECRET=' /var/www/mywave/.env | cut -d= -f2-)"

curl -s "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -d "url=https://mywavewake.ru/api/online-coaching/telegram/webhook" \
  -d "secret_token=${WEBHOOK_SECRET}" \
  -d "allowed_updates=[\"message\",\"edited_message\"]"
```

Ожидание: `"ok":true`

### Проверка webhook

```bash
curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo" | python3 -m json.tool
```

### Перезапуск сайта

```bash
sudo systemctl restart mywave-site
sleep 12
```

### E2E (тестовая заявка)

1. Сайт → Online Coaching → анкета `video_check`
2. Скопировать `oc_req_...` с экрана success
3. В Telegram notification-бот: отправить **видео** с подписью:
   ```
   oc_req_XXXXXXXXXXXX
   Разбор: держать баланс в волне
   ```
4. Admin: статус `video_received`, Telegram тренеру «Новые материалы»

---

## 4. MAX / WhatsApp — PR-модуль D

HTTP-адаптеры: нужны URL и token от вашего провайдера MAX/WhatsApp Business API.

### .env

```env
ONLINE_COACHING_CHANNEL_NOTIFY_ENABLED=1
MAX_API_URL=https://ВАШ_MAX_ENDPOINT/send
MAX_API_TOKEN=ВАШ_MAX_TOKEN
WHATSAPP_API_URL=
WHATSAPP_API_TOKEN=
```

### Перезапуск

```bash
sudo systemctl restart mywave-site
sleep 12
```

### Проверка (заявка с preferred_channel=max)

1. Новая заявка с каналом MAX
2. В логах:
   ```bash
   sudo journalctl -u mywave-site -n 100 --no-pager | grep online_coaching_max
   ```
3. `online_coaching_max_send ok=True` — успех; `skipped` — нет credentials

---

## Rollback по модулям (без отката кода)

```bash
# В .env выключить нужный флаг:
# ONLINE_COACHING_TBANK_API_ENABLED=0
# ONLINE_COACHING_REMINDERS_ENABLED=0
# ONLINE_COACHING_TELEGRAM_VIDEO_UPLOAD_ENABLED=0
# ONLINE_COACHING_CHANNEL_NOTIFY_ENABLED=0

sudo systemctl restart mywave-site
```

Для Telegram video дополнительно удалить webhook:

```bash
curl -s "https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook"
```

---

## Полный чеклист после включения всех модулей

```bash
cd /var/www/mywave && source venv/bin/activate
set -a && source .env && set +a

curl -sf https://mywavewake.ru/health/live
curl -sf https://mywavewake.ru/services/online-coaching | grep -q 'oc_req'

python scripts/run_online_coaching_reminders.py --dry-run
pytest tests/unit/test_online_coaching_phase2.py -q

sudo journalctl -u mywave-site -n 50 --no-pager | grep -E 'online_coaching|tbank|reminder' || true
```

---

## PR-стратегия (4 отдельных merge)

| PR | Модуль | Можно включать на prod независимо |
|----|--------|-----------------------------------|
| #91 | Reminders cron | `ONLINE_COACHING_REMINDERS_ENABLED` |
| #92 | T-Bank API | `ONLINE_COACHING_TBANK_API_ENABLED` |
| #93 | Telegram video | `ONLINE_COACHING_TELEGRAM_VIDEO_UPLOAD_ENABLED` |
| #94 | MAX/WhatsApp | `ONLINE_COACHING_CHANNEL_NOTIFY_ENABLED` |

Код Phase 1 (ручная ссылка T-Bank, Telegram тренеру) работает без Phase 2 flags.
