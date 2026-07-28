# Owner runbook — YClients S8 → S9 → S10 (после Camp hold)

**Дата:** 2026-07-29  
**Camp:** public ON, cron OFF, Tour отладка — **не трогаем** до реальных кемпов.  
**S7 GCal:** PASS (уже).

## Prod status (2026-07-28/29) — CLOSED

| Волна | Результат |
|-------|-----------|
| S5 read | PASS |
| S6 write | PASS |
| S7 GCal mirror | PASS + cron |
| S8 TGbot gateway | PASS · PR [#16](https://github.com/YaroslavValeev/TGK_MyWave/pull/16) MERGED |
| S9 Site boat + phone | PASS · Site PR [#117](https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/117) MERGED |
| S10 cancel/reschedule | PASS (TG E2E create→reschedule→cancel) |

**Канон:** boat SoT = YClients · Site+TG → gateway · GCal mirror · Sheets `yc-{id}` · slot 25+5=30 · gym = legacy.

Сервер Site: `/var/www/mywave` · `mywave-site`  
Бот: `/opt/mywave-bot` · `mywave-telegram-bot`  
**Не трогать:** `mywave-node`

---

## S8 — verify TGbot gateway

### S8-1 Status

```bash
systemctl is-active mywave-site mywave-telegram-bot
grep -E '^BOOKING_GATEWAY_|^YCLIENTS_WRITE_ENABLED=' /opt/mywave-bot/.env || true
grep -E '^YCLIENTS_GATEWAY_SECRET=|^YCLIENTS_ENABLED=|^BOAT_PROVIDER=' /var/www/mywave/.env | sed 's/\(SECRET=\).*/\1***MASKED***/'
```

**Ожидаемо бот:** `BOOKING_GATEWAY_ENABLED=1`, `BOOKING_GATEWAY_URL=https://mywavewake.ru/api/internal/yclients`, secret = Site, `YCLIENTS_WRITE_ENABLED=0` на боте.

### S8-2 Site gateway health

```bash
cd /var/www/mywave
GW=$(grep '^YCLIENTS_GATEWAY_SECRET=' .env | cut -d= -f2-)
curl -sS "https://mywavewake.ru/api/internal/yclients/health" \
  -H "X-MyWave-Gateway-Secret: ${GW}"
curl -sS "https://mywavewake.ru/api/internal/yclients/slots?date=2026-08-05" \
  -H "X-MyWave-Gateway-Secret: ${GW}" | head -c 500; echo
```

### S8-3 Bot client smoke

```bash
cd /opt/mywave-bot
source venv/bin/activate
python - <<'PY'
from dotenv import load_dotenv
load_dotenv('.env', override=True)
from services.booking_settings import BookingSettings
from services.booking_gateway import BookingGatewayClient
c = BookingGatewayClient(BookingSettings.from_env())
print(c.health())
print(c.list_slots('2026-08-05'))
PY
```

### S8-4 Enable gateway (если OFF)

```bash
# только если BOOKING_GATEWAY_ENABLED != 1
# SECRET must match Site YCLIENTS_GATEWAY_SECRET
sudo sed -i 's/^BOOKING_GATEWAY_ENABLED=.*/BOOKING_GATEWAY_ENABLED=1/' /opt/mywave-bot/.env
# ensure URL:
grep -q '^BOOKING_GATEWAY_URL=' /opt/mywave-bot/.env \
  || echo 'BOOKING_GATEWAY_URL=https://mywavewake.ru/api/internal/yclients' | sudo tee -a /opt/mywave-bot/.env
sudo sed -i 's/^YCLIENTS_WRITE_ENABLED=.*/YCLIENTS_WRITE_ENABLED=0/' /opt/mywave-bot/.env
sudo systemctl restart mywave-telegram-bot
sleep 3
systemctl is-active mywave-telegram-bot
```

**Rollback bot:**
```bash
sudo sed -i 's/^BOOKING_GATEWAY_ENABLED=.*/BOOKING_GATEWAY_ENABLED=0/' /opt/mywave-bot/.env
sudo systemctl restart mywave-telegram-bot
```

**S8 PASS:** health ok + list_slots не пустой (или пустой день без слотов) + TG ручной: Запись→Катер→подтверждение.

---

## S9 — Site boat UI + phone

### S9-1 Hero → Site modal (не виджет)

```bash
cd /var/www/mywave
TS=$(date +%Y%m%d_%H%M%S)
sudo cp -a .env ".env.bak_s9_${TS}"

sudo python3 - <<'PY'
from pathlib import Path
p = Path('/var/www/mywave/.env')
lines = p.read_text().splitlines()
out, seen_hero = [], False
for line in lines:
    if line.startswith('HERO_BOOKING_EXTERNAL_URL='):
        out.append('HERO_BOOKING_EXTERNAL_URL=')
        seen_hero = True
    elif line.startswith('BOAT_PROVIDER='):
        out.append('BOAT_PROVIDER=yclients')
    else:
        out.append(line)
if not seen_hero:
    out.append('HERO_BOOKING_EXTERNAL_URL=')
if not any(l.startswith('BOAT_PROVIDER=') for l in out):
    out.append('BOAT_PROVIDER=yclients')
p.write_text('\n'.join(out) + '\n')
print('ok')
PY

grep -E '^HERO_BOOKING_EXTERNAL_URL=|^BOAT_PROVIDER=|^YCLIENTS_ENABLED=|^YCLIENTS_WRITE_ENABLED=' .env
sudo chown www-data:www-data .env && sudo chmod 600 .env
sudo systemctl restart mywave-site
sleep 4
systemctl is-active mywave-site
curl -fsS https://mywavewake.ru/health
```

### S9-2 Public boat slots

```bash
# дата со слотами — подставьте актуальную
curl -sS "https://mywavewake.ru/api/calendar/slots/2026-08-05?service=boat" | python3 -m json.tool | head -50
```

### S9-3 Unit (Site)

```bash
cd /var/www/mywave && source venv/bin/activate
pytest -q tests/unit/test_boat_yclients_pipeline.py --tb=line
```

### S9-4 Bot phone + restart

```bash
cd /opt/mywave-bot && source venv/bin/activate
python -m unittest tests.test_booking_settings_gateway -v
sudo systemctl restart mywave-telegram-bot
sleep 3
systemctl is-active mywave-telegram-bot
python - <<'PY'
from dotenv import load_dotenv
load_dotenv('.env', override=True)
from services.booking_settings import BookingSettings
from services.booking_gateway import BookingGatewayClient, resolve_client_phone
c = BookingGatewayClient(BookingSettings.from_env())
print(c.health())
print('phone', resolve_client_phone(contact_phone='89161234567', telegram_user_id='1'))
PY
```

**S9 PASS:** слоты boat с Site API = YClients; hero открывает модалку Site; TG phone prompt работает.

**Rollback S9:**
```bash
sudo sed -i 's/^BOAT_PROVIDER=.*/BOAT_PROVIDER=calendar/' /var/www/mywave/.env
# optionally restore widget URL
sudo systemctl restart mywave-site
```

---

## S10 — cancel / reschedule smoke

```bash
cd /var/www/mywave && source venv/bin/activate
set -a && source .env && set +a
python - <<'PY'
from app import create_app
from app.services.booking.providers.yclients import get_yclients_provider, parse_attendance_status
import os, requests

app = create_app()
SECRET = os.environ['YCLIENTS_GATEWAY_SECRET']
BASE = 'https://mywavewake.ru/api/internal/yclients'
H = {'X-MyWave-Gateway-Secret': SECRET, 'Content-Type': 'application/json'}
DATE = '2026-08-05'

with app.app_context():
    p = get_yclients_provider()
    slots = [s.start_time for s in p.fetch_available_slots(DATE)]
    print('slots', slots)
    if len(slots) < 2:
        raise SystemExit('need >=2 free slots on ' + DATE)
    t = slots[-1]
    t2 = slots[-2]
    created = p.create_booking(
        date_str=DATE, time_str=t, client_name='S10 Smoke',
        client_phone='79160000888', set_count=1, source='site',
        internal_id='s10-smoke', use_online=False,
    )
    rid = created.external_id
    print('created', rid, t)
    r = requests.patch(f'{BASE}/bookings/{rid}', headers=H,
                       json={'datetime': f'{DATE} {t2}:00'}, timeout=30)
    print('patch', r.status_code, r.text[:300])
    r2 = requests.post(f'{BASE}/bookings/{rid}/cancel', headers=H, timeout=30)
    print('cancel', r2.status_code, r2.text[:300])
    rec = p.get_record(rid)
    life = parse_attendance_status(rec.get('attendance'), deleted=bool(rec.get('deleted')))
    print('lifecycle', life)
    print('S10 SMOKE PASS' if life in ('cancelled', 'deleted') else 'S10 SMOKE FAIL')
PY
```

**S10 PASS:** patch 200 + cancel 200 + lifecycle cancelled.

---

## После S10 — Blog (следующий этап)

Порядок:
1. Blog editorial standard + ParserNews contract  
2. Blog video + CSP  
3. Admin Blog write workflow  
4. **S11** final Site audit  

Отдельный runbook Blog — после вашего GO.

---

## Порядок выполнения сегодня

1. **S8-1 → S8-3** (verify; S8-4 только если gateway OFF)  
2. **S9-1 → S9-4**  
3. **S10 smoke**  
4. Пришлите выводы — зафиксируем PASS и откроем Blog
