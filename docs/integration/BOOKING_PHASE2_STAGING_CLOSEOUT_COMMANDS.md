# BOOKING Phase 2 — Staging close-out (S5 + S8 + S9)

**Audience:** Owner / Site ops (SSH на staging-хост)  
**Prod:** не трогать (`mywave-site`, `mywave-node`, `mywave-telegram-bot`, TGbotAdmin prod).

Скрипты: `automation/staging/` в репозитории.

---

## 0. Одна команда (рекомендуется)

**Если `git pull` падает на local changes** (staging-only, prod не трогаем):

```bash
cd /var/www/mywave-staging
sudo -u www-data git fetch origin main
sudo -u www-data git reset --hard origin/main
sudo -u www-data git rev-parse HEAD
# ожидается: 6d07b9c1 или новее
grep -q 'def _curl' automation/staging/_client.py && echo "client_ok"
```

Затем close-out:

```bash
cd /var/www/mywave-staging && \
export STAGING_ROOT=/var/www/mywave-staging && \
export STAGING_SPREADSHEET_ID=16Ewm8Npv3bkNH37X-KAm3PWmRedQ1a8xoiO6LPggyBI && \
sudo -u www-data env STAGING_ROOT="$STAGING_ROOT" STAGING_SPREADSHEET_ID="$STAGING_SPREADSHEET_ID" \
  bash automation/staging/run_closeout.sh
```

**Важно:** не запускать S9/S8 в shell с export prod `SPREADSHEET_ID`. Скрипты читают `/var/www/mywave-staging/.env` с `override` (last key wins).

Артефакты: `/tmp/staging_closeout_YYYYMMDD_HHMMSS/`  
Приложить GM: `s8_calendar.json`, `s5_buffer.log`, `s9_orphan.log`.

---

## 1. Предусловия

```bash
curl -fsS http://127.0.0.1:5002/health | python3 -m json.tool
grep -E '^BOOKING_PHASE2_' /var/www/mywave-staging/.env
sudo systemctl is-active mywave-staging
```

Ожидается: health `database` + `google` OK; все 5 `BOOKING_PHASE2_*=1`; `active`.

Smoke S1–S4/S6 уже выполнен на **`2026-06-12`** (boat 07:00, gym 16:00) — нужен для S8.

---

## 2. S8 — Calendar API dump (Variant B)

```bash
cd /var/www/mywave-staging
source venv/bin/activate
export SECRET_KEY="$(grep -E '^SECRET_KEY=' .env | cut -d= -f2-)"
export S8_DATE="2026-06-12"

python3 automation/staging/s8_calendar_dump.py | tee /tmp/s8_calendar.json
```

**PASS:** stdout содержит `"s8_pass": true` и строку `S8_ok`.

---

## 3. S5 — full travel buffer

Использует **чистые даты** (не перезаписывает smoke 2026-06-12):

| Часть | Дата | Действие |
|-------|------|----------|
| B gym→boat | `2026-06-13` (сб) | gym 10:00 → boat 12:00 blocked, 13:30 OK |
| A boat→gym | `2026-06-20` (сб) | boat 12:00 → gym 14:00 blocked, 14:30 OK |

Скрипт при необходимости добавит в Schedule строки `14:00` / `14:30` для субботы.

```bash
cd /var/www/mywave-staging
source venv/bin/activate
export STAGING_BASE_URL="http://127.0.0.1:5002"
export SECRET_KEY="$(grep -E '^SECRET_KEY=' .env | cut -d= -f2-)"

python3 automation/staging/s5_travel_buffer.py | tee /tmp/s5_buffer.log
```

**PASS:** последняя строка `S5_ok`.

---

## 4. S9 — orphan re-check

```bash
cd /var/www/mywave-staging
source venv/bin/activate
export SECRET_KEY="$(grep -E '^SECRET_KEY=' .env | cut -d= -f2-)"

python3 automation/staging/s9_orphan_check.py
```

**PASS:** `orphan_count 0` + `S9_ok`.

---

## 5. S7 — TGbotAdmin (не Site, ручной)

1. TGbotAdmin → **staging** calendar ID (не prod).
2. Одна bot-бронь → summary `(ID: tg_user_id)`.
3. Одна web-бронь → `(WEB_ID: bk_…)`.
4. Parser не считает WEB_ID дубликатом ID.

Evidence: скриншоты Calendar + подтверждение от TGbotAdmin.

---

## 6. pytest (опционально, regression)

```bash
cd /var/www/mywave-staging
source venv/bin/activate
BOOKING_PHASE2_AVAILABILITY=0 \
BOOKING_PHASE2_TRAVEL_BUFFER=0 \
BOOKING_PHASE2_MULTI_SET_BOAT=0 \
BOOKING_PHASE2_SUMMARY_V2=0 \
BOOKING_PHASE2_GYM_LOCATION_V2=0 \
ENABLE_GOOGLE_SERVICES=0 \
python -m pytest tests/unit/test_booking_*.py tests/unit/test_booking_features.py -q
```

Ожидается: **87 passed**.

---

## 7. Что НЕ делать

```bash
# ЗАПРЕЩЕНО до GM approval:
sudo systemctl restart mywave-site
sudo systemctl restart mywave-node.service
sudo systemctl restart mywave-telegram-bot.service
# не менять /var/www/mywave/.env BOOKING_PHASE2_*
```
