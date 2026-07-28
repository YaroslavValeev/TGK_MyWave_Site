# YCLIENTS S7 — Google Calendar mirror GO (28.07.2026)

**Статус:** PASS (`SMOKE GCAL PASS`)  
**Цепочка:** YCLIENTS SoT → GCal mirror (закрытый) → Sheets позже

---

## Что сделано

- Upsert события по `extendedProperties.private.yclients_record_id`
- Summary: `Катер MyWave — {имя}`
- Description: телефон, услуга, source (`mw_source=`), record_id
- Cancel / delete webhook → удаление события из GCal
- Webhook обогащает sparse payload через `GET /record`
- Флаг: `YCLIENTS_GCAL_MIRROR_ENABLED=1`

---

## Команды проверки

```bash
cd /var/www/mywave
source venv/bin/activate
set -a; source .env; set +a
export YCLIENTS_ENABLED=1 YCLIENTS_WRITE_ENABLED=1 YCLIENTS_GCAL_MIRROR_ENABLED=1

python scripts/yclients_smoke_gcal.py --date 2026-07-31
```

Dry-run reconcile (без записи в GCal):

```bash
python scripts/sync_yclients_bookings.py --days-back 1 --days-forward 14
```

Apply reconcile:

```bash
python scripts/sync_yclients_bookings.py --apply --days-back 1 --days-forward 14
```

Webhook → audit:

```bash
tail -n 10 /var/www/mywave/instance/yclients_webhook_events.jsonl
```

---

## Cron (рекомендуется)

```bash
sudo tee /etc/cron.d/mywave-yclients-gcal >/dev/null <<'EOF'
*/15 * * * * www-data cd /var/www/mywave && ./venv/bin/python scripts/sync_yclients_bookings.py --apply --days-back 1 --days-forward 21 >> /var/log/mywave-yclients-gcal.log 2>&1
EOF
sudo chmod 644 /etc/cron.d/mywave-yclients-gcal
sudo touch /var/log/mywave-yclients-gcal.log
sudo chown www-data:www-data /var/log/mywave-yclients-gcal.log
```

---

## Rollback mirror

```bash
sudo sed -i 's/^YCLIENTS_GCAL_MIRROR_ENABLED=.*/YCLIENTS_GCAL_MIRROR_ENABLED=0/' /var/www/mywave/.env
sudo systemctl restart mywave-site
```

---

## Следующая волна

1. TGbotAdmin → Site gateway (без прямого YCLIENTS write)
2. Site boat booking → gateway вместо только виджета
3. Sheets audit row по record_id
