# Booking Seasonal + YCLIENTS Prep — deploy-note (Owner)

**Сервис:** только `mywave-site` (`/var/www/mywave`)  
**Не трогать:** `mywave-node`, `mywave-telegram-bot`, TGbotAdmin  
**Camp production:** отдельный STOP — не смешивать с booking deploy.

---

## Фаза 0 — Owner (сейчас, без deploy)

### 0.1 YCLIENTS вручную (критичнее кода)

Компания `2043174`:

| День | Правило | Период |
|------|---------|--------|
| Понедельник | нерабочий день | до 30.09.2026 |
| Четверг | перерыв 16:00–20:00 | до 30.09.2026 |

Виджет катера: `https://n347190.yclients.com/company/2043174/personal/menu?o=`

### 0.2 Письмо в YCLIENTS support

```
Здравствуйте!

Необходимо подключить API-интеграцию для компании YCLIENTS ID 2043174 с сайтом и Telegram-ботом MyWave.

Цели интеграции:
1. Получать актуальное расписание единственного сотрудника.
2. Получать свободные интервалы для онлайн-записи.
3. Создавать записи с сайта MyWave и из Telegram-бота.
4. Получать созданные, изменённые, перенесённые и отменённые записи.
5. Синхронизировать записи с закрытым Google Calendar.
6. Получать имя, фамилию, телефон, услугу, сотрудника, дату, время, длительность и статус записи.
7. Исключать дубли по уникальному ID записи YCLIENTS.

Просим предоставить или подтвердить:
- доступ компании 2043174 к API;
- тип требуемой авторизации;
- токен приложения / партнёрский токен;
- пользовательский токен, если он требуется;
- ID сотрудника;
- ID услуг;
- endpoints для расписания, свободных слотов, записей, создания, изменения и отмены;
- возможность подключения webhook для событий создания, изменения и отмены записи;
- документацию по webhook payload;
- ограничения запросов API;
- необходимость публикации интеграции через Marketplace;
- наличие тестового контура.

Webhook планируется принимать по HTTPS на домене mywavewake.ru.
```

### 0.3 Read-only audit на production

```bash
set -euo pipefail

PROD_ROOT=/var/www/mywave
GIT="git -c safe.directory=${PROD_ROOT}"
TS=$(date +%Y%m%d_%H%M%S)

cd "$PROD_ROOT"

echo "=== CURRENT STATE ==="
echo "head=$($GIT rev-parse HEAD)"
echo "branch=$($GIT branch --show-current)"
systemctl is-active mywave-site || true

echo "=== BACKUP ==="
if [ -x deploy/scripts/backup_mywave.sh ]; then
  sudo deploy/scripts/backup_mywave.sh
else
  sudo tar \
    --exclude='./venv' \
    --exclude='./.git' \
    -czf "/root/mywave_before_schedule_${TS}.tar.gz" .
fi

echo "=== FIND BOOKING SCHEDULE IMPLEMENTATION ==="
grep -RInE \
  "GYM|gym|boat|capacity|available_slots|availability|schedule_policy|BOOKING_SEASONAL" \
  app static/js tests config.py env.example \
  2>/dev/null \
  | head -n 300 \
  | tee "/root/mywave_booking_schedule_audit_${TS}.txt"

echo "=== CHECK ENV FLAGS WITHOUT VALUES ==="
python3 - <<'PY'
from pathlib import Path

path = Path(".env")
names = {
    line.split("=", 1)[0].strip()
    for line in path.read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.lstrip().startswith("#") and "=" in line
}

wanted = [
    "BOOKING_SEASONAL_RULES_ENABLED",
    "BOOKING_SEASONAL_RULES_UNTIL",
    "GYM_SEASONAL_WEEKDAYS",
    "GYM_SEASONAL_START_TIME",
    "YCLIENTS_ENABLED",
    "YCLIENTS_COMPANY_ID",
    "YCLIENTS_PARTNER_TOKEN",
    "YCLIENTS_USER_TOKEN",
]

for name in wanted:
    print(f"{name}: {'present' if name in names else 'missing'}")
PY

echo "=== DONE — NO PRODUCTION CHANGES APPLIED ==="
```

---

## Фаза 5 — Production deploy (только после merge PR + Owner GO)

Подставить `EXPECTED_HEAD` после merge booking PR в `main`.

```bash
set -euo pipefail

PROD_ROOT=/var/www/mywave
GIT="git -c safe.directory=${PROD_ROOT}"
EXPECTED_HEAD="<ПОЛНЫЙ_HASH_MAIN_ПОСЛЕ_MERGE>"
TS=$(date +%Y%m%d_%H%M%S)

cd "$PROD_ROOT"

echo "=== PRECHECK ==="
test "$($GIT branch --show-current)" = "main"

echo "=== BACKUP ==="
if [ -x deploy/scripts/backup_mywave.sh ]; then
  sudo deploy/scripts/backup_mywave.sh
fi

echo "=== UPDATE ==="
$GIT fetch origin main
$GIT checkout main
$GIT pull --ff-only origin main
ACTUAL_HEAD=$($GIT rev-parse HEAD)
echo "actual_head=$ACTUAL_HEAD"
test "$ACTUAL_HEAD" = "$EXPECTED_HEAD"

echo "=== ENV: SEASONAL RULES ==="
python3 - <<'PY'
from pathlib import Path

path = Path(".env")
updates = {
    "BOOKING_SEASONAL_RULES_ENABLED": "1",
    "BOOKING_SEASONAL_RULES_UNTIL": "2026-09-30",
    "GYM_SEASONAL_WEEKDAYS": "0,3",
    "GYM_SEASONAL_START_TIME": "19:00",
    "GYM_SEASONAL_DURATION_MINUTES": "90",
    "GYM_CAPACITY": "4",
    "BOAT_PROVIDER": "yclients",
    "BOAT_SLOT_DURATION_MINUTES": "30",
    "BOAT_CAPACITY": "1",
    "YCLIENTS_ENABLED": "0",
    "YCLIENTS_COMPANY_ID": "2043174",
    "YCLIENTS_WIDGET_URL": "https://n347190.yclients.com/company/2043174/personal/menu?o=",
}

lines = path.read_text(encoding="utf-8").splitlines()
seen = set()
result = []

for line in lines:
    stripped = line.strip()
    if stripped and not stripped.startswith("#") and "=" in line:
        key = line.split("=", 1)[0].strip()
        if key in updates:
            result.append(f"{key}={updates[key]}")
            seen.add(key)
            continue
    result.append(line)

for key, value in updates.items():
    if key not in seen:
        result.append(f"{key}={value}")

path.write_text("\n".join(result) + "\n", encoding="utf-8")
PY

sudo chown www-data:www-data .env
sudo chmod 600 .env

echo "=== TESTS ==="
source venv/bin/activate
pytest \
  tests/unit/test_booking_schedule_policy.py \
  tests/unit/test_booking_client_display.py \
  tests/unit/test_yclients_provider.py \
  tests/integration/test_yclients_webhook.py \
  tests/unit/test_booking_phase1.py \
  -q

echo "=== RESTART SITE ONLY ==="
sudo systemctl restart mywave-site
sleep 8

echo "=== HEALTH ==="
systemctl is-active mywave-site
curl -fsS https://mywavewake.ru/health/live

echo "=== SMOKE GYM SEASONAL ==="
# Monday 2026-07-13 — only 19:00
curl -s "https://mywavewake.ru/api/calendar/slots/2026-07-13?service=gym" | head -c 400
echo
# Tuesday 2026-07-14 — empty or no slots
curl -s "https://mywavewake.ru/api/calendar/slots/2026-07-14?service=gym" | head -c 200
echo

sudo journalctl -u mywave-site --since "-5 minutes" --no-pager -l | tail -n 80
```

### Rollback

```bash
cd /var/www/mywave
git -c safe.directory=/var/www/mywave checkout <PREV_HEAD>
# в .env: BOOKING_SEASONAL_RULES_ENABLED=0
sudo systemctl restart mywave-site
curl -fsS https://mywavewake.ru/health/live
```

---

## Env reference

| Variable | Prod (seasonal ON) | Notes |
|----------|-------------------|-------|
| `BOOKING_SEASONAL_RULES_ENABLED` | `1` | OFF до GO |
| `BOOKING_SEASONAL_RULES_UNTIL` | `2026-09-30` | auto-off 2026-10-01 |
| `GYM_SEASONAL_WEEKDAYS` | `0,3` | Mon, Thu |
| `GYM_SEASONAL_START_TIME` | `19:00` | 90 min → 20:30 |
| `YCLIENTS_ENABLED` | `0` | до credentials + smoke |
| `BOOKING_OPERATIONAL_SUMMARY_ENABLED` | `0` | `1` после проверки GCal format |

---

## Acceptance

- [ ] Mon/Thu 19:00 slots only until 2026-09-30
- [ ] POST gym on Tue → 409 `gym_seasonal_schedule_restricted`
- [ ] 2026-10-01+ base schedule
- [ ] `YCLIENTS_ENABLED=0` on prod
- [ ] Boat → YCLIENTS widget (не Site calendar для новых)
- [ ] Camp production не затронут
