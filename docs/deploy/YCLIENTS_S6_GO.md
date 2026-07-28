# YCLIENTS S6 — controlled write GO (28.07.2026)

**Статус:** PASS  
**Флаги prod:** `YCLIENTS_ENABLED=1`, `YCLIENTS_WRITE_ENABLED=1`, read=on  
**Не трогать:** `mywave-node`, `mywave-telegram-bot` (пока без прямого write)

---

## Что работает

| Операция | Статус |
|----------|--------|
| Слоты `book_times` | PASS |
| Create journal `POST /records` | PASS |
| Cancel `attendance=-1` (full PUT merge) | PASS |
| Gateway create/cancel | PASS |
| Webhook endpoint + audit jsonl | PASS |
| GCal mirror upsert | pending (следующая волна) |

### Зафиксированные ID

- Company: `2043174` (Loaded x MyWave)
- Staff (слоты): `5660610` — Катер Axis A24
- Default service: `30120744` — Вейксерф 25 мин + тренировка
- Partner + Owner User token — в `.env`

---

## Webhook URL (в ЛК YCLIENTS)

```bash
grep '^YCLIENTS_WEBHOOK_SECRET=' /var/www/mywave/.env | sed 's/^YCLIENTS_WEBHOOK_SECRET=/https:\/\/mywavewake.ru\/public\/integrations\/yclients\/webhook?token=/'
```

События: record create / update / delete.  
Аудит на сервере: `/var/www/mywave/instance/yclients_webhook_events.jsonl`

Проверка:

```bash
SECRET=$(grep '^YCLIENTS_WEBHOOK_SECRET=' /var/www/mywave/.env | cut -d= -f2-)
curl -sS -X POST "https://mywavewake.ru/public/integrations/yclients/webhook?token=${SECRET}" \
  -H 'Content-Type: application/json' \
  -d '{"company_id":2043174,"resource":"record","resource_id":1,"status":"create","data":{"id":1,"attendance":0}}'
tail -n 3 /var/www/mywave/instance/yclients_webhook_events.jsonl
```

---

## Smoke команды

```bash
cd /var/www/mywave
source venv/bin/activate
set -a; source .env; set +a
export YCLIENTS_ENABLED=1 YCLIENTS_READ_ONLY_ENABLED=1 YCLIENTS_WRITE_ENABLED=1

python scripts/yclients_smoke_read.py --date 2026-07-31
python scripts/yclients_smoke_write.py --date 2026-07-31
```

Gateway:

```bash
GW=$(grep '^YCLIENTS_GATEWAY_SECRET=' /var/www/mywave/.env | cut -d= -f2-)
curl -sS "https://mywavewake.ru/api/internal/yclients/health" \
  -H "X-MyWave-Gateway-Secret: ${GW}"
curl -sS "https://mywavewake.ru/api/internal/yclients/slots?date=2026-07-31" \
  -H "X-MyWave-Gateway-Secret: ${GW}"
```

---

## Rollback WRITE

```bash
cd /var/www/mywave
sudo sed -i 's/^YCLIENTS_WRITE_ENABLED=.*/YCLIENTS_WRITE_ENABLED=0/' .env
sudo systemctl restart mywave-site
curl -fsS https://mywavewake.ru/health/live
```

Полный off:

```bash
sudo sed -i 's/^YCLIENTS_ENABLED=.*/YCLIENTS_ENABLED=0/' .env
sudo systemctl restart mywave-site
```

---

## Следующая волна

1. GCal mirror upsert по `record_id` (idempotent)
2. Подключить TGbotAdmin → gateway (без прямого YCLIENTS write)
3. Site boat booking → gateway вместо только виджета
4. Custom fields `mw_source` / `mw_internal_id` в ЛК YCLIENTS
