# BOOKING_PHASE2 — Final Staging E2E Package

**Версия:** 2.0 (execution-ready)
**Дата:** 2026-06-05
**Статус:** ready for Owner setup — **не включать flags на production**
**Prod baseline:** PR #18 deployed GREEN (`67b30510`), flags OFF

**Participants:** Site Owner + TGbotAdmin (+ optional QA)

**Связанные документы:**

- [`BOOKING_PHASE2_STAGING_SMOKE.md`](BOOKING_PHASE2_STAGING_SMOKE.md) — чеклист с галочками
- [`BOOKING_SHEETS_ORPHAN_CLEANUP_RUNBOOK.md`](../operations/BOOKING_SHEETS_ORPHAN_CLEANUP_RUNBOOK.md)
- [`BOOKING_PHASE2_PR18_DEPLOY_PACKAGE.md`](BOOKING_PHASE2_PR18_DEPLOY_PACKAGE.md)

---

## 0. Owner protocol (заполнить перед стартом)

```text
STAGING_BASE_URL=___________________________
STAGING_ROOT=/var/www/mywave-staging
STAGING_BIND=127.0.0.1:5002
STAGING_GOOGLE_CALENDAR_ID=_________________  # tail: …
STAGING_SPREADSHEET_ID=_____________________  # tail: …
STAGING_SERVICE_ACCOUNT=instance/service_account.json
STAGING_GIT_HEAD=___________________________
STAGING_TEST_DATE=__________________________  # YYYY-MM-DD, будний день
STAGING_SMOKE_PHONE=+7999000XXXX            # тестовый диапазон, не prod PII
```

---

## 1. Staging contour / URL

### 1.1 Рекомендация (Option A — тот же VPS, изоляция от prod)

| Параметр | Значение |
|----------|----------|
| **Root** | `/var/www/mywave-staging` |
| **systemd** | `mywave-staging.service` |
| **Bind** | `127.0.0.1:5002` (prod `mywave-site` = `:5000`, `mywave-node` = `:5001`) |
| **URL (вариант 1)** | `https://staging.mywavewake.ru` → nginx proxy → `:5002` |
| **URL (вариант 2)** | SSH tunnel: `ssh -L 5002:127.0.0.1:5002 user@host` → `http://127.0.0.1:5002` |

**Запрещено для E2E с flags ON:**

- `https://mywavewake.ru` (production)
- prod `GOOGLE_CALENDAR_ID` / `SPREADSHEET_ID`
- restart `mywave-node.service` / `mywave-telegram-bot.service` без отдельного approval

### 1.2 Production (не трогать в staging session)

| Item | Value |
|------|-------|
| URL | `https://mywavewake.ru` |
| Root | `/var/www/mywave` |
| HEAD | `67b30510` (PR #18) |
| Flags | **OFF / absent** |

---

## 2. Test Calendar ID

### 2.1 Создание (Owner)

1. Google Calendar → **Создать календарь** → имя: `MyWave Staging Booking`.
2. Скопировать **Calendar ID** (формат `xxxx@group.calendar.google.com`).
3. Записать в staging `.env` как `GOOGLE_CALENDAR_ID`.

### 2.2 Требования

- **Отдельный** от production calendar.
- Пустой или с тестовыми событиями только staging smoke.
- Timezone календаря: `Europe/Moscow`.

### 2.3 Проверка доступа SA

```bash
cd "$STAGING_ROOT"
source venv/bin/activate
export SECRET_KEY="$(grep -E '^SECRET_KEY=' .env | cut -d= -f2-)"

python - <<'PY'
from app import create_app
app = create_app()
with app.app_context():
    from app.services.google import get_google_services
    _, _, cal = get_google_services()
    cid = app.config["GOOGLE_CALENDAR_ID"]
    cal.calendarList().get(calendarId=cid).execute()
    print("calendar_ok", cid[-12:])
PY
```

---

## 3. Test Spreadsheet ID

### 3.1 Создание (Owner)

1. Создать Google Sheet `MyWave Staging Booking`.
2. Листы (минимум): `Clients`, `Workouts`, `Client_Workouts`, `Schedule` — структура как prod, **без prod PII**.
3. Скопировать **Spreadsheet ID** из URL.
4. Записать в staging `.env` как `SPREADSHEET_ID`.

### 3.2 Проверка

```bash
cd "$STAGING_ROOT"
source venv/bin/activate
export SECRET_KEY="$(grep -E '^SECRET_KEY=' .env | cut -d= -f2-)"

python - <<'PY'
from app import create_app
app = create_app()
with app.app_context():
    from app.modules.sheets_access import get_google_sheet
    for name in ("Workouts", "Client_Workouts", "Clients"):
        s = get_google_sheet(name)
        print(name, "rows", len(s.values))
PY
```

---

## 4. Service account permissions

| Ресурс | Permission | Как выдать |
|--------|------------|------------|
| Staging Calendar | **Make changes to events** | Calendar → Settings → Share → SA email → role Editor |
| Staging Spreadsheet | **Editor** | Sheet → Share → SA email |
| SA key file | Read on host | `instance/service_account.json` (можно копия prod SA или отдельный ключ) |

**SA email:** взять из `service_account.json` → поле `client_email`.

**Не давать** SA editor на **production** calendar/sheet, если используете тот же SA file — достаточно share только staging ресурсов.

---

## 5. BOOKING_PHASE2_* flags для staging (ALL ON)

Добавить **только** в `/var/www/mywave-staging/.env`:

```bash
BOOKING_PHASE2_AVAILABILITY=1
BOOKING_PHASE2_TRAVEL_BUFFER=1
BOOKING_PHASE2_MULTI_SET_BOAT=1
BOOKING_PHASE2_SUMMARY_V2=1
BOOKING_PHASE2_GYM_LOCATION_V2=1
```

| Flag | Зависимость |
|------|-------------|
| `BOOKING_PHASE2_TRAVEL_BUFFER=1` | требует `BOOKING_PHASE2_AVAILABILITY=1` |
| `BOOKING_PHASE2_MULTI_SET_BOAT=1` | рекомендуется с `AVAILABILITY=1` |

**Production `.env` — не менять.**

---

## 6. Smoke-сценарии (обязательные)

Исполнять на **staging** с flags ON. Evidence: скрин UI + ссылка Calendar event + orphan check.

| ID | Сценарий | Pass criteria |
|----|----------|---------------|
| **S1** | Катер single set | 1 event 30 min; summary v2 `Тренировка — Катер — 1 сет — …`; `extendedProperties.private.set_count=1`; 2-й клиент на тот же slot → **409** |
| **S2** | Катер multi-set (3) | UI picker 1..3; 1 continuous event 90 min; preview `start–end`; POST `set_count:3`; summary `3 сета`; blocks 18:00+18:30 range |
| **S3** | Grid 07:00–19:30 | GET boat slots: first `07:00`, last `19:30`, count **26**; нет 06:00 / 20:00 |
| **S4** | Зал 0/4–4/4 | API `remaining` 4→1; 4 bookings OK; 5-й → **409** `gym_capacity_full` |
| **S5** | Travel buffer 120 min | Boat 12:00–12:30 → gym before 14:30 blocked; gym 10:00–11:30 → boat before 13:30 blocked |
| **S6** | Race GET → POST → 409 | Tab A GET slot free → Tab B books → Tab A POST → **409**, no orphan Workouts |
| **S7** | WEB_ID / ID separation | Web summary `(WEB_ID: bk_…)`; TGbotAdmin event `(ID: tg_id)` unchanged; bot не путает маркеры |
| **S8** | Calendar contract | Gym: location `Зал`, duration 90 min; Boat: location `Катер`, duration N×30, `set_count` in extended props |
| **S9** | No orphan rows | После S1–S6: `orphan_count 0` (script §8.3); после forced partial fail — compensation + runbook |
| **S10** | Flags OFF regression (optional) | Clone staging `.env` flags=0 → Phase 1 POST, no multi-set picker |

### 6.1 API helpers (GET slots)

Подставить `STAGING_BASE_URL` и `DATE`:

```bash
export STAGING_BASE_URL="https://staging.mywavewake.ru"
export DATE="2026-06-12"

curl -fsS "${STAGING_BASE_URL}/api/calendar/slots/${DATE}?service=boat" | python3 -m json.tool | head -40

curl -fsS "${STAGING_BASE_URL}/api/calendar/slots/${DATE}?service=gym" | python3 -m json.tool | head -40
```

**Boat grid check:**

```bash
curl -fsS "${STAGING_BASE_URL}/api/calendar/slots/${DATE}?service=boat" | python3 - <<'PY'
import sys, json
slots = json.load(sys.stdin)
times = [s["time"] for s in slots if s.get("available", True)]
print("count", len(times), "first", times[0] if times else None, "last", times[-1] if times else None)
assert times[0] == "07:00", times[0]
assert times[-1] == "19:30", times[-1]
print("grid_ok")
PY
```

### 6.2 POST booking

**Рекомендуется:** UI (`booking.js`) — CSRF через сессию.

Payload reference (boat 3 sets):

```json
{
  "date": "2026-06-12",
  "time": "18:00",
  "name": "Staging Test Boat",
  "phone": "+79990001234",
  "service_type": "boat",
  "set_count": 3
}
```

Endpoint: `POST /api/calendar/book` — success 200; conflict **409**; duplicate **400**.

### 6.3 TGbotAdmin joint (S6, S7)

- Bot booking на staging calendar (test user only).
- Web + bot race на один slot → один success, один 409.
- Проверить summary markers в Calendar UI.

---

## 7. Rollback / disable plan

### 7.1 Staging disable (вернуть Phase 1 на staging)

```bash
cd /var/www/mywave-staging
nano .env
```

Установить или удалить:

```bash
BOOKING_PHASE2_AVAILABILITY=0
BOOKING_PHASE2_TRAVEL_BUFFER=0
BOOKING_PHASE2_MULTI_SET_BOAT=0
BOOKING_PHASE2_SUMMARY_V2=0
BOOKING_PHASE2_GYM_LOCATION_V2=0
```

```bash
sudo systemctl restart mywave-staging
```

### 7.2 Staging teardown (полный откат контура)

```bash
sudo systemctl stop mywave-staging
sudo systemctl disable mywave-staging
# nginx: убрать server block staging.mywavewake.ru
# данные: staging calendar/sheet можно очистить вручную
```

### 7.3 Production

**Не менять** prod `.env` flags до отдельного GM approval после **Staging GREEN**.

---

## 8. Exact Owner commands

### 8.1 One-time staging bootstrap

```bash
export STAGING_ROOT=/var/www/mywave-staging

sudo mkdir -p "$STAGING_ROOT"
sudo chown www-data:www-data "$STAGING_ROOT"

cd "$STAGING_ROOT"
sudo -u www-data git clone https://github.com/YaroslavValeev/TGK_MyWave_Site.git .
sudo -u www-data git checkout main
sudo -u www-data git pull --ff-only origin main
sudo -u www-data git rev-parse HEAD

sudo -u www-data python3.11 -m venv venv
sudo -u www-data bash -c "source venv/bin/activate && pip install -r requirements.txt"

sudo mkdir -p "$STAGING_ROOT/instance" "$STAGING_ROOT/logs"
sudo cp /var/www/mywave/instance/service_account.json "$STAGING_ROOT/instance/"
sudo cp /var/www/mywave/.env "$STAGING_ROOT/.env"
sudo chown -R www-data:www-data "$STAGING_ROOT"
```

### 8.2 Configure staging `.env` (Owner edits)

```bash
cd /var/www/mywave-staging
nano .env
```

Заменить / добавить:

```bash
GOOGLE_CALENDAR_ID=<staging_test_calendar>@group.calendar.google.com
SPREADSHEET_ID=<staging_test_spreadsheet_id>
SERVER_NAME=https://staging.mywavewake.ru
TIMEZONE=Europe/Moscow

BOOKING_PHASE2_AVAILABILITY=1
BOOKING_PHASE2_TRAVEL_BUFFER=1
BOOKING_PHASE2_MULTI_SET_BOAT=1
BOOKING_PHASE2_SUMMARY_V2=1
BOOKING_PHASE2_GYM_LOCATION_V2=1
```

Проверка:

```bash
grep -E '^(GOOGLE_CALENDAR_ID|SPREADSHEET_ID|BOOKING_PHASE2_)' /var/www/mywave-staging/.env
```

### 8.3 Install systemd + start staging

```bash
sudo cp /var/www/mywave-staging/deploy/systemd/mywave-staging.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mywave-staging
sudo systemctl start mywave-staging
sudo systemctl is-active mywave-staging
```

**Не выполнять:**

```bash
sudo systemctl restart mywave-site
sudo systemctl restart mywave-node.service
sudo systemctl restart mywave-telegram-bot.service
```

### 8.4 Staging pytest (before smoke)

```bash
cd /var/www/mywave-staging
source venv/bin/activate
export SECRET_KEY="$(grep -E '^SECRET_KEY=' .env | cut -d= -f2-)"

python -m pytest \
  tests/unit/test_booking_grid.py \
  tests/unit/test_booking_pipeline_phase2.py \
  tests/unit/test_booking_features.py \
  tests/unit/test_booking_calendar_v2.py \
  tests/unit/test_booking_calendar_reader_buffer.py \
  tests/unit/test_booking_availability_phase2.py \
  tests/unit/test_booking_phase1.py \
  tests/unit/test_booking_orchestrator_context.py \
  tests/unit/test_booking_service.py \
  tests/unit/test_boat_slots.py \
  tests/unit/test_booking_sheets_compensation.py \
  -q --tb=short
```

**Expected:** `87 passed`

### 8.5 Orphan check (после smoke S1–S9)

```bash
cd /var/www/mywave-staging
source venv/bin/activate
export SECRET_KEY="$(grep -E '^SECRET_KEY=' .env | cut -d= -f2-)"

python - <<'PY'
from app import create_app
from app.services.google_sheets_service import read_records

app = create_app()
with app.app_context():
    sid = app.config["SPREADSHEET_ID"]
    workouts = read_records(sid, "Workouts")
    cw = read_records(sid, "Client_Workouts")
    cw_ids = {str(r.get("workout_id") or "") for r in cw if r.get("workout_id")}
    orphans = []
    for w in workouts:
        wid = str(w.get("workout_id") or "")
        if not wid:
            continue
        status = (w.get("workout_status") or "").strip().lower()
        if status == "cancelled":
            continue
        if wid not in cw_ids:
            orphans.append(wid[-8:])
    print("orphan_count", len(orphans))
    for t in orphans[:20]:
        print("orphan_tail", t)
PY
```

**Expected:** `orphan_count 0`

### 8.6 Staging health smoke

```bash
export STAGING_BASE_URL="https://staging.mywavewake.ru"

curl -fsS "${STAGING_BASE_URL}/health"
curl -fsS -o /dev/null -w "home %{http_code}\n" "${STAGING_BASE_URL}/"
```

---

## 9. Go / No-Go

| Gate | Criteria |
|------|----------|
| **Staging GREEN** | S1–S9 PASS + pytest 87 + orphan_count 0 + TGbotAdmin sign-off |
| **Prod flags ON** | Отдельное GM approval; по одному flag за шаг (см. STAGING_SMOKE §10) |

---

## 10. Evidence deliverable (после smoke)

Owner / Site присылают:

1. `STAGING_BASE_URL` + `git rev-parse HEAD`
2. Flags snapshot (grep `BOOKING_PHASE2_`)
3. Calendar links: boat 1-set, boat 3-set, gym 4/4
4. Screenshots: multi-set picker, confirm button
5. Race test: 409 + no orphan
6. `orphan_count 0` output
7. TGbotAdmin: PASS / issues
8. pytest: `87 passed`

---

## 11. Constraints (напоминание)

До отдельного approval:

- production flags ON — **не включать**
- production `.env` — **не менять**
- `mywave-site` — **не рестартить** без deploy-окна
- `mywave-node.service` / `mywave-telegram-bot.service` — **не трогать**
