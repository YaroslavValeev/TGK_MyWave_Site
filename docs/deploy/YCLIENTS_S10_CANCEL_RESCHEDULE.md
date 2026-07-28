# YCLIENTS S10 — Cancel / Reschedule / Sheets journal (28.07.2026)

**Статус:** code ready  
**Multi-set:** без изменений (одна запись, `seance × N`).

## Канон

```
TG cancel boat
  → gateway POST /bookings/{id}/cancel
     → YCLIENTS attendance=-1
     → Sheets yc-{id} → cancelled / отменено
     → GCal mirror delete
  → bot GCal delete (best-effort)

TG reschedule boat
  → gateway list_slots (дата)
  → gateway PATCH /bookings/{id} {datetime}
     → YCLIENTS SoT
     → GCal mirror upsert
  → bot GCal update (duration = slot 30×N)

Gym cancel/reschedule — legacy Calendar (без YCLIENTS).
```

## Команды на сервере

```bash
# 0) restart после деплоя кода
sudo systemctl restart mywave-site mywave-telegram-bot
sleep 3
systemctl is-active mywave-site mywave-telegram-bot

# 1) unit
cd /var/www/mywave && source venv/bin/activate
pytest -q tests/unit/test_yclients_sheets_cancel.py tests/unit/test_boat_yclients_pipeline.py --tb=line
cd /opt/mywave-bot && source venv/bin/activate
python -m unittest tests.test_booking_settings_gateway -v

# 2) smoke: create → reschedule → cancel (не трогает живые записи клиентов)
cd /var/www/mywave && source venv/bin/activate
set -a && source .env && set +a
python - <<'PY'
from app import create_app
from app.services.booking.providers.yclients import get_yclients_provider, parse_attendance_status
from app.services.booking.sheets_writer import mark_yclients_journal_cancelled
import os, requests

app = create_app()
SECRET = os.environ['YCLIENTS_GATEWAY_SECRET']
BASE = 'https://mywavewake.ru/api/internal/yclients'
H = {'X-MyWave-Gateway-Secret': SECRET, 'Content-Type': 'application/json'}

with app.app_context():
    p = get_yclients_provider()
    slots = [s.start_time for s in p.fetch_available_slots('2026-07-31')]
    # pick late free slot
    t = next(x for x in ('20:30','20:00','19:30','18:00') if x in slots)
    created = p.create_booking(
        date_str='2026-07-31', time_str=t, client_name='S10 Smoke',
        client_phone='79160000888', set_count=1, source='site',
        internal_id='s10-smoke', use_online=False,
    )
    rid = created.external_id
    print('created', rid, t)

    # reschedule via gateway to another free slot
    slots2 = [s.start_time for s in p.fetch_available_slots('2026-07-31')]
    t2 = next(x for x in slots2 if x != t)
    r = requests.patch(f'{BASE}/bookings/{rid}', headers=H,
                       json={'datetime': f'2026-07-31 {t2}:00'}, timeout=30)
    print('patch', r.status_code, r.json())

    # cancel via gateway
    r2 = requests.post(f'{BASE}/bookings/{rid}/cancel', headers=H, timeout=30)
    print('cancel', r2.status_code, r2.json())

    rec = p.get_record(rid)
    life = parse_attendance_status(rec.get('attendance'), deleted=bool(rec.get('deleted')))
    print('lifecycle', life)
    try:
        p.delete_booking(rid)
        print('hard-deleted', rid)
    except Exception as e:
        print('delete', e)
PY

# 3) webhook audit tail
sudo tail -n 20 /var/www/mywave/instance/yclients_webhook_events.jsonl 2>/dev/null || echo 'no webhook audit yet'

# 4) cron mirror exists?
ls -la /etc/cron.d/mywave-yclients-gcal 2>/dev/null
sudo journalctl -u mywave-site --since '10 minutes ago' --no-pager | grep -iE 'cancel|patch|mirror|sheets' | tail -30
```

## Ручной E2E в Telegram

1. Запись на катер (короткий слот).
2. Мои тренировки → **Перенести** → дата/время из YClients слотов → подтвердить → YClients + GCal сдвинуты.
3. Мои тренировки → **Отменить** → YClients cancelled, GCal нет, Sheets `yc-*` cancelled.

## Rollback

```bash
# только bot gateway off (cancel/reschedule снова GCal-only для новых путей)
sudo sed -i 's/^BOOKING_GATEWAY_ENABLED=.*/BOOKING_GATEWAY_ENABLED=0/' /opt/mywave-bot/.env
sudo systemctl restart mywave-telegram-bot
```
