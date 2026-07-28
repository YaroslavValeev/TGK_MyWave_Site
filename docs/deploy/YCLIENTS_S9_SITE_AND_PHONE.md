# YCLIENTS S9 — Site public boat + TGbot phone/cancel (28.07.2026)

**Статус:** code ready · apply + restart via commands below  
**Канон:**

```
Site UI /api/calendar/slots?service=boat  → YCLIENTS (in-process)
Site UI /api/calendar/book (boat)         → YCLIENTS create → Sheets yc-{id} → GCal mirror
Telegram boat                             → Site gateway → YCLIENTS (как S8)
                                           + contact phone (fallback synthetic)
                                           + cancel → gateway cancel + GCal delete
Gym                                       → legacy Calendar/Sheets (без изменений)
```

## Что изменилось

| Слой | Изменение |
|------|-----------|
| Site `get_boat_slots` | При `BOAT_PROVIDER=yclients` + read → слоты из YCLIENTS |
| Site `execute_web_booking` | Boat + write → `provider.create_booking(source=site)`, без прямого GCal |
| Site Sheets | `workout_id=yc-{record_id}` |
| TGbot phone | contact → stored → synthetic |
| TGbot cancel | `yclients_record_id` из GCal private props → gateway cancel |

## Команды на сервере (выполнить по порядку)

```bash
# 0) статус до
systemctl is-active mywave-site mywave-telegram-bot

# 1) Site: hero CTA обратно на модалку Site (пустой URL), не внешний виджет
#    (после проверки API можно оставить пустым навсегда)
sudo python3 - <<'PY'
from pathlib import Path
p = Path('/var/www/mywave/.env')
lines = p.read_text().splitlines()
out, seen = [], False
for line in lines:
    if line.startswith('HERO_BOOKING_EXTERNAL_URL='):
        out.append('HERO_BOOKING_EXTERNAL_URL=')
        seen = True
    else:
        out.append(line)
if not seen:
    out.append('HERO_BOOKING_EXTERNAL_URL=')
# ensure boat provider
if not any(l.startswith('BOAT_PROVIDER=') for l in out):
    out.append('BOAT_PROVIDER=yclients')
else:
    out = [('BOAT_PROVIDER=yclients' if l.startswith('BOAT_PROVIDER=') else l) for l in out]
p.write_text('\n'.join(out) + '\n')
print('HERO_BOOKING_EXTERNAL_URL cleared; BOAT_PROVIDER=yclients')
PY

# 2) unit-тесты Site (быстрые)
cd /var/www/mywave && source venv/bin/activate
pytest -q tests/unit/test_boat_yclients_pipeline.py tests/unit/test_boat_slots.py tests/unit/test_booking_phase1.py --tb=line

# 3) restart site
sudo systemctl restart mywave-site
sleep 3
systemctl is-active mywave-site

# 4) smoke Site boat slots (публичный API)
curl -sS "https://mywavewake.ru/api/calendar/slots/2026-07-31?service=boat" | python3 -m json.tool | head -40

# 5) smoke create через gateway (как сайт in-process, но проверяем write path)
cd /var/www/mywave && source venv/bin/activate
set -a && source .env && set +a
python - <<'PY'
from app import create_app
from app.services.booking.providers.yclients import get_yclients_provider
app = create_app()
with app.app_context():
    p = get_yclients_provider()
    slots = p.fetch_available_slots('2026-07-31')
    print('slots', [s.start_time for s in slots][:8])
PY

# 6) TGbot unit + restart
cd /opt/mywave-bot && source venv/bin/activate
python -m unittest tests.test_booking_settings_gateway -v
sudo systemctl restart mywave-telegram-bot
sleep 3
systemctl is-active mywave-telegram-bot

# 7) bot gateway health
python - <<'PY'
from dotenv import load_dotenv
load_dotenv('.env', override=True)
from services.booking_settings import BookingSettings
from services.booking_gateway import BookingGatewayClient, resolve_client_phone
c = BookingGatewayClient(BookingSettings.from_env())
print(c.health())
print('phone', resolve_client_phone(contact_phone='89161234567', telegram_user_id='1'))
print(c.list_slots('2026-07-31'))
PY

# 8) логи
sudo journalctl -u mywave-site --since '5 minutes ago' --no-pager | grep -iE 'boat|yclient' | tail -30
sudo journalctl -u mywave-telegram-bot --since '5 minutes ago' --no-pager | grep -iE 'gateway|yclient|boat' | tail -20
```

## Ручной E2E

1. **Site:** открыть mywavewake.ru → Записаться (модалка) → Катер → 31.07 → слот → телефон реальный → подтвердить → запись в YCLIENTS + `yc-*` в Sheets + GCal mirror.
2. **TG:** Запись → Катер → слот → «Поделиться телефоном» или «Пропустить» → подтверждение.
3. **TG cancel:** Мои тренировки → Отменить (для mirrored boat) → запись cancelled в YCLIENTS.

## Rollback

```bash
# Site: вернуть Calendar boat + виджет hero
sudo sed -i 's/^BOAT_PROVIDER=.*/BOAT_PROVIDER=calendar/' /var/www/mywave/.env
sudo sed -i 's|^HERO_BOOKING_EXTERNAL_URL=.*|HERO_BOOKING_EXTERNAL_URL=https://n347190.yclients.com/company/2043174/personal/menu?o=|' /var/www/mywave/.env
# или только write off (слоты ещё из YC если BOAT_PROVIDER=yclients):
# sudo sed -i 's/^YCLIENTS_WRITE_ENABLED=.*/YCLIENTS_WRITE_ENABLED=0/' /var/www/mywave/.env
sudo systemctl restart mywave-site

# Bot gateway off
sudo sed -i 's/^BOOKING_GATEWAY_ENABLED=.*/BOOKING_GATEWAY_ENABLED=0/' /opt/mywave-bot/.env
sudo systemctl restart mywave-telegram-bot
```

## Slot model (канон)

| Понятие | Минуты | Где |
|---------|--------|-----|
| Катание (seance) | **25** | YCLIENTS `seance_length`, услуга |
| Тех. буфер (пирс) | **5** | не отдельная запись; входит в слот |
| Календарный слот | **30** | UI «18:30–19:00», GCal end, Sheets `duration`, шаг сетки |

Env: `BOAT_SEANCE_MINUTES=25`, `BOAT_SLOT_DURATION_MINUTES=30`.

YCLIENTS journal показывает `18:30–18:55`, но сетка/book_times блокирует полный 30‑мин слот до следующего старта.

---

## Критерий готовности

- [ ] `/api/calendar/slots/...?service=boat` = слоты YCLIENTS
- [ ] Site boat book → record в YCLIENTS, Sheets `yc-{id}`, GCal mirror
- [ ] Gym book без регрессии
- [ ] TG phone prompt + synthetic fallback
- [ ] TG cancel boat → YCLIENTS cancelled
