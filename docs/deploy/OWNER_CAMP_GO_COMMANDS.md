# Owner — Camp GO (import + cron)

**Дата:** 2026-07-29  
**Контекст:** S11 full CLOSED · Owner GO на Camp  
**Сервис:** только `mywave-site` · **не** трогать `mywave-node`  
**Публичка `/camps`:** уже LIVE через Tour API (не зависит от local import)

**Что включаем сейчас:** один ручной import в локальную БД → verify → cron на `run_camp_sync.py`  
**Что не делаем:** `flask db upgrade` вслепую · rewrite cron через `tee` · restart bot/node

---

## Важно

| Поверхность | Источник |
|-------------|----------|
| `/camps` | Tour API (LIVE) |
| `/admin/camp`, `/api/camps` | локальная БД после sync |

Старый cron на prod был:
`#0 */6 … flask camp-sync` — **без** gate `CAMP_IMPORT_ENABLED`.  
При enable переписываем на `scripts/run_camp_sync.py` (есть gate).

`flask camp-sync` на prod **не** использовать как primary.

---

## Phase 1 — Diagnose (read-only) → пришлите вывод

```bash
cd /var/www/mywave
git log -1 --oneline
systemctl is-active mywave-site mywave-telegram-bot
curl -fsS https://mywavewake.ru/health | python3 -c 'import sys,json; print(json.load(sys.stdin).get("status"))'
curl -sS -o /dev/null -w "camps %{http_code}\n" https://mywavewake.ru/camps

grep -E '^CAMP_|^MYWAVE_TOUR_' .env | sed 's/\(TOKEN=\).*/\1***MASKED***/'

echo '=== cron file ==='
ls -la /etc/cron.d/mywave-camp* 2>/dev/null || echo 'no camp cron file'
cat /etc/cron.d/mywave-camp-sync 2>/dev/null || echo 'missing'
```

```bash
cd /var/www/mywave
source venv/bin/activate
set -a; source .env; set +a
python scripts/check_tour_camp_api.py
```

**PASS Phase 1:** health ok · `/camps` 200 · flags видны · Tour preflight `OK: list items=…`  
**FAIL 401/5xx Tour:** STOP — sync/cron не трогать.

---

## Phase 2 — Import ON + один sync (только после Phase 1 PASS)

```bash
cd /var/www/mywave
TS=$(date +%Y%m%d_%H%M%S)
sudo cp -a .env ".env.bak_camp_go_${TS}"

# import must be 1 for run_camp_sync.py
grep -q '^CAMP_IMPORT_ENABLED=' .env \
  && sudo sed -i 's/^CAMP_IMPORT_ENABLED=.*/CAMP_IMPORT_ENABLED=1/' .env \
  || echo 'CAMP_IMPORT_ENABLED=1' | sudo tee -a .env >/dev/null

grep -q '^CAMP_MODULE_ENABLED=' .env \
  && sudo sed -i 's/^CAMP_MODULE_ENABLED=.*/CAMP_MODULE_ENABLED=1/' .env \
  || echo 'CAMP_MODULE_ENABLED=1' | sudo tee -a .env >/dev/null

grep -E '^CAMP_MODULE_ENABLED=|^CAMP_IMPORT_ENABLED=|^CAMP_PUBLIC_ENABLED=|^CAMP_ADMIN_ENABLED=' .env
sudo chown www-data:www-data .env
sudo chmod 600 .env
```

```bash
cd /var/www/mywave
sudo -u www-data env FLASK_CONFIG=production ./venv/bin/python scripts/run_camp_sync.py
# ожидаемо: camp_sync: {'fetched': N, 'created': …, 'updated': …, …}
# skip: camp_sync: CAMP_IMPORT_ENABLED=0 — тогда проверьте Phase 2 sed
```

```bash
curl -fsS https://mywavewake.ru/health | python3 -c 'import sys,json; print(json.load(sys.stdin).get("status"))'
curl -sS -o /dev/null -w "camps %{http_code}\n" https://mywavewake.ru/camps
curl -sS -o /dev/null -w "admin_camp %{http_code}\n" https://mywavewake.ru/admin/camp/
# 302/200 — норма для admin
```

**UI:** `/admin/camp/` — новые в `pending_review` / `possible_duplicate`.  
**PASS Phase 2:** sync stats без `failed` · health ok · `/camps` 200.

---

## Phase 3 — Enable cron (только после Phase 2 PASS)

```bash
sudo cp -a /etc/cron.d/mywave-camp-sync "/etc/cron.d/mywave-camp-sync.bak_$(date +%Y%m%d_%H%M%S)"
cat /etc/cron.d/mywave-camp-sync
```

Заменить содержимое на канон с gate (не `flask camp-sync`):

```bash
sudo tee /etc/cron.d/mywave-camp-sync >/dev/null <<'EOF'
# MyWave Camp sync — every 6h via run_camp_sync.py (honors CAMP_IMPORT_ENABLED)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

0 */6 * * * www-data cd /var/www/mywave && FLASK_CONFIG=production /var/www/mywave/venv/bin/python /var/www/mywave/scripts/run_camp_sync.py >> /var/log/mywave/camp-sync.log 2>&1
EOF

sudo chmod 644 /etc/cron.d/mywave-camp-sync
# файл лога
sudo mkdir -p /var/log/mywave
sudo touch /var/log/mywave/camp-sync.log
sudo chown www-data:www-data /var/log/mywave/camp-sync.log

echo '=== cron active line ==='
grep -nE '^\s*[^#].*run_camp_sync|^\s*0 \*/6' /etc/cron.d/mywave-camp-sync
cat /etc/cron.d/mywave-camp-sync
```

**PASS Phase 3:** активная строка без `#` · путь `run_camp_sync.py` · user `www-data`.

---

## Rollback (< 1 мин)

```bash
# вернуть cron HOLD
sudo cp -a /etc/cron.d/mywave-camp-sync.bak_YYYYMMDD_HHMMSS /etc/cron.d/mywave-camp-sync
# или закомментировать:
# sudo sed -i 's/^\(0 \*\/6.*run_camp_sync.*\)/#\1/' /etc/cron.d/mywave-camp-sync
cat /etc/cron.d/mywave-camp-sync

# soft-stop дальнейших sync
# sudo sed -i 's/^CAMP_IMPORT_ENABLED=.*/CAMP_IMPORT_ENABLED=0/' /var/www/mywave/.env
```

Уже импортированные строки в БД rollback cron **не удаляет**.

---

## Не делать

- restart `mywave-node`  
- mass publish всех `pending_review` без модерации  
- `flask camp-sync` вместо `run_camp_sync.py`  
- Camp GO одновременно с другими большими деплоями  

После Phase 3 PASS — пришлите вывод; отметим **Camp CLOSED**.
