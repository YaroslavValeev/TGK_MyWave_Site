# YCLIENTS S8 — TGbot → Site gateway (28.07.2026)

**Статус:** PASS (client smoke create+cancel)  
**Prod bot:** `/opt/mywave-bot` · service `mywave-telegram-bot`

## Канон

```
Telegram bot (boat)
   → Site /api/internal/yclients/*
      → YCLIENTS SoT
         → GCal mirror (webhook/cron)
Gym остаётся legacy Calendar/Sheets path.
```

Bot **никогда** не ставит `YCLIENTS_WRITE_ENABLED=1`.

## Env бота

```bash
BOOKING_GATEWAY_ENABLED=1
BOOKING_GATEWAY_URL=https://mywavewake.ru/api/internal/yclients
BOOKING_GATEWAY_SECRET=<same as site YCLIENTS_GATEWAY_SECRET>
YCLIENTS_WRITE_ENABLED=0
```

## Команды

```bash
# статус
systemctl is-active mywave-telegram-bot mywave-site

# smoke gateway из бота
cd /opt/mywave-bot
source venv/bin/activate
python - <<'PY'
from dotenv import load_dotenv
load_dotenv('.env', override=True)
from services.booking_settings import BookingSettings
from services.booking_gateway import BookingGatewayClient
c = BookingGatewayClient(BookingSettings.from_env())
print(c.health())
print(c.list_slots('2026-07-31'))
PY

# логи бота
sudo journalctl -u mywave-telegram-bot --since '10 minutes ago' --no-pager | tail -n 50

# rollback gateway
sudo sed -i 's/^BOOKING_GATEWAY_ENABLED=.*/BOOKING_GATEWAY_ENABLED=0/' /opt/mywave-bot/.env
sudo systemctl restart mywave-telegram-bot
```

## Ручной E2E в Telegram

1. Открыть бота → Запись → Катер
2. Выбрать дату с слотами YCLIENTS (например 31.07)
3. Подтвердить 1 сет
4. Ожидание: «Запись подтверждена» + запись в YCLIENTS + событие в GCal через mirror

## Следующая волна

См. [YCLIENTS_S9_SITE_AND_PHONE.md](./YCLIENTS_S9_SITE_AND_PHONE.md):
- Site public boat → YCLIENTS in-process
- Реальный телефон в TGbot (contact share)
- Cancel boat через gateway
