# Owner runbook — S7 GCal mirror GO → Camp diagnose (2026-07-28)

Сервер: `4169037-ep26382` / `62.113.42.227`  
cwd: `/var/www/mywave`  
Restart OK: только `mywave-site.service`  
**Не трогать:** `mywave-node`, `mywave-telegram-bot`, TGbotAdmin

Код S7 уже в `main` (GCal mirror + smoke script). На сервере: флаги → smoke → cron → затем Camp diagnose.

---

## S7 — Google Calendar mirror

### S7-1 Preflight

```bash
cd /var/www/mywave
git rev-parse HEAD
systemctl is-active mywave-site.service
curl -fsS https://mywavewake.ru/health
grep -E '^YCLIENTS_ENABLED=|^YCLIENTS_WRITE_ENABLED=|^YCLIENTS_GCAL_MIRROR_ENABLED=|^YCLIENTS_READ_ONLY_ENABLED=|^BOAT_PROVIDER=|^GOOGLE_CALENDAR_ID=' .env || true
ls -la instance/yclients_webhook_events.jsonl 2>/dev/null || echo "no webhook audit yet"
ls /etc/cron.d/mywave-yclients* 2>/dev/null || echo "no yclients cron"
```

**Ожидаемо:** HEAD ≥ `dec7e5d1`, site `active`, health ok.

### S7-2 Enable mirror flag

```bash
cd /var/www/mywave
TS=$(date +%Y%m%d_%H%M%S)
sudo cp -a .env ".env.bak_s7_${TS}"

grep -q '^YCLIENTS_GCAL_MIRROR_ENABLED=' .env \
  && sudo sed -i 's/^YCLIENTS_GCAL_MIRROR_ENABLED=.*/YCLIENTS_GCAL_MIRROR_ENABLED=1/' .env \
  || echo 'YCLIENTS_GCAL_MIRROR_ENABLED=1' | sudo tee -a .env >/dev/null

# write must stay ON for smoke create/cancel
grep -q '^YCLIENTS_WRITE_ENABLED=' .env \
  && sudo sed -i 's/^YCLIENTS_WRITE_ENABLED=.*/YCLIENTS_WRITE_ENABLED=1/' .env \
  || echo 'YCLIENTS_WRITE_ENABLED=1' | sudo tee -a .env >/dev/null

grep -q '^YCLIENTS_ENABLED=' .env \
  && sudo sed -i 's/^YCLIENTS_ENABLED=.*/YCLIENTS_ENABLED=1/' .env \
  || echo 'YCLIENTS_ENABLED=1' | sudo tee -a .env >/dev/null

grep -E '^YCLIENTS_ENABLED=|^YCLIENTS_WRITE_ENABLED=|^YCLIENTS_GCAL_MIRROR_ENABLED=' .env
sudo chown www-data:www-data .env
sudo chmod 600 .env
sudo systemctl restart mywave-site.service
sleep 4
systemctl is-active mywave-site.service
curl -fsS https://mywavewake.ru/health
```

**Rollback:**

```bash
sudo sed -i 's/^YCLIENTS_GCAL_MIRROR_ENABLED=.*/YCLIENTS_GCAL_MIRROR_ENABLED=0/' /var/www/mywave/.env
sudo systemctl restart mywave-site.service
```

### S7-3 Smoke GCal

```bash
cd /var/www/mywave
source venv/bin/activate
set -a; source .env; set +a
export YCLIENTS_ENABLED=1 YCLIENTS_WRITE_ENABLED=1 YCLIENTS_GCAL_MIRROR_ENABLED=1 DISABLE_TELEGRAM=1

# если FAIL: no slots — смените дату на день со свободным слотом катера
python scripts/yclients_smoke_gcal.py --date 2026-08-05
```

**PASS:** строка `SMOKE GCAL PASS <record_id>`  
**FAIL:** пришлите полный stdout + `journalctl -u mywave-site -n 50 --no-pager`

### S7-4 Reconcile

```bash
cd /var/www/mywave
source venv/bin/activate
set -a; source .env; set +a
python scripts/sync_yclients_bookings.py --days-back 1 --days-forward 14
python scripts/sync_yclients_bookings.py --apply --days-back 1 --days-forward 14
```

### S7-5 Cron

```bash
sudo tee /etc/cron.d/mywave-yclients-gcal >/dev/null <<'EOF'
*/15 * * * * www-data cd /var/www/mywave && ./venv/bin/python scripts/sync_yclients_bookings.py --apply --days-back 1 --days-forward 21 >> /var/log/mywave-yclients-gcal.log 2>&1
EOF
sudo chmod 644 /etc/cron.d/mywave-yclients-gcal
sudo touch /var/log/mywave-yclients-gcal.log
sudo chown www-data:www-data /var/log/mywave-yclients-gcal.log
ls -la /etc/cron.d/mywave-yclients-gcal
```

**Rollback cron:** `sudo rm -f /etc/cron.d/mywave-yclients-gcal`

### S7-6 Audit (optional)

```bash
tail -n 20 /var/www/mywave/instance/yclients_webhook_events.jsonl 2>/dev/null || echo empty
journalctl -u mywave-site.service -n 40 --no-pager | grep -iE 'yclients|gcal|mirror' || true
```

### S7 acceptance

- [ ] `YCLIENTS_GCAL_MIRROR_ENABLED=1`
- [ ] `SMOKE GCAL PASS`
- [ ] cron установлен
- [ ] health ok

---

## Camp — diagnose (только после S7 PASS)

**Не включать import/cron**, пока preflight Tour API не OK.  
Публичная витрина (`CAMP_PUBLIC`) — отдельным решением после diagnose.

### CAMP-1 Flags + HTTP

```bash
cd /var/www/mywave
grep -E '^CAMP_|^MYWAVE_TOUR_' .env | sed 's/\(TOKEN=\).*/\1***MASKED***/'
systemctl is-active mywave-site.service
curl -sS -o /tmp/camps_http.txt -w "%{http_code}\n" https://mywavewake.ru/camps
head -c 200 /tmp/camps_http.txt; echo
ls /etc/cron.d/mywave-camp* 2>/dev/null || echo "no camp cron (good if STOP)"
```

### CAMP-2 Tour API preflight

```bash
cd /var/www/mywave
source venv/bin/activate
set -a; source .env; set +a
python scripts/check_tour_camp_api.py
```

**PASS:** `OK: list items=...`  
**FAIL 401/404:** Camp остаётся OFF — нужен Tour. Не включать public/import.

### CAMP-3 (только если CAMP-2 PASS) — включить public showcase

```bash
cd /var/www/mywave
TS=$(date +%Y%m%d_%H%M%S)
sudo cp -a .env ".env.bak_camp_${TS}"

grep -q '^CAMP_MODULE_ENABLED=' .env \
  && sudo sed -i 's/^CAMP_MODULE_ENABLED=.*/CAMP_MODULE_ENABLED=1/' .env \
  || echo 'CAMP_MODULE_ENABLED=1' | sudo tee -a .env >/dev/null

grep -q '^CAMP_PUBLIC_ENABLED=' .env \
  && sudo sed -i 's/^CAMP_PUBLIC_ENABLED=.*/CAMP_PUBLIC_ENABLED=1/' .env \
  || echo 'CAMP_PUBLIC_ENABLED=1' | sudo tee -a .env >/dev/null

# import/cron пока OFF — отдельный GO
grep -q '^CAMP_IMPORT_ENABLED=' .env \
  && sudo sed -i 's/^CAMP_IMPORT_ENABLED=.*/CAMP_IMPORT_ENABLED=0/' .env \
  || echo 'CAMP_IMPORT_ENABLED=0' | sudo tee -a .env >/dev/null

grep -E '^CAMP_' .env
sudo chown www-data:www-data .env
sudo chmod 600 .env
sudo systemctl restart mywave-site.service
sleep 4
curl -sS -o /dev/null -w "%{http_code}\n" https://mywavewake.ru/camps
curl -fsS https://mywavewake.ru/health
```

**Rollback Camp public:**

```bash
sudo sed -i 's/^CAMP_PUBLIC_ENABLED=.*/CAMP_PUBLIC_ENABLED=0/' /var/www/mywave/.env
sudo systemctl restart mywave-site.service
```

### CAMP-4 — НЕ делать без отдельного GO

```bash
# НЕ запускать пока Owner не даст GO на import:
# sudo -u www-data ./venv/bin/python scripts/run_camp_sync.py
# sudo tee /etc/cron.d/mywave-camp-sync ...
```

---

## Порядок выполнения Owner

1. S7-1 → S7-2 → S7-3 → S7-4 → S7-5  
2. Пришлите `SMOKE GCAL PASS`  
3. CAMP-1 → CAMP-2  
4. Если CAMP-2 PASS → CAMP-3 (public only)  
5. Import/cron Camp — только после вашего отдельного GO
