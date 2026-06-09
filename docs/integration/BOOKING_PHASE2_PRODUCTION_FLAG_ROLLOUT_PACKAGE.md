# BOOKING Phase 2 — Production Flag Rollout Package

**From:** Site MyWave  
**To:** GM / Owner  
**Date:** 2026-06-08  
**Staging gate:** **GREEN WITH CAVEAT** (S5/S8/S9 PASS, S7 read-only PASS)  
**Production status:** **FLAGS OFF — DO NOT EXECUTE until separate GM approval**

---

## 0. Executive summary

| Item | Value |
|------|--------|
| **Purpose** | Enable `BOOKING_PHASE2_*` on production **only** `mywave-site` |
| **Code baseline (repo `main`)** | `27f2d886` — `docs(booking): staging close-out PASS S5/S8/S9, TGbotAdmin S7 handoff` |
| **Staging evidence HEAD** | `1ecbd161` (close-out smoke) + docs `27f2d886` |
| **Recommended strategy** | **Controlled stepped rollout** (5 restarts) — see §5 |
| **Fast-path alternative** | Single bundle (all 5 flags) — only if GM accepts one restart + full smoke |
| **Services to restart** | **`mywave-site` only** |
| **Services forbidden** | `mywave-node.service`, `mywave-telegram-bot.service`, TGbotAdmin prod |

**Caveat (non-blocking):** staging `s8_calendar.json` had no live Telegram `(ID: tg_id)` event; WEB_ID collision not found; TGbotAdmin regression tests cover legacy marker. Optional: targeted Telegram smoke before flags ON (§5.6).

---

## 1. Current production HEAD

### 1.1 Repository baseline (GitHub `main`)

```text
27f2d8869ddb269f09e081aa7d10694fb65ee844
docs(booking): staging close-out PASS S5/S8/S9, TGbotAdmin S7 handoff
```

**Pre-rollout:** production server should be on this commit **or newer** on `main` (includes full Phase 2 code path; flags default OFF in code).

**If production HEAD is `67b30510`:** execute code-only deploy first — [`BOOKING_PHASE2_PRODUCTION_CODE_ONLY_DEPLOY_PACKAGE.md`](BOOKING_PHASE2_PRODUCTION_CODE_ONLY_DEPLOY_PACKAGE.md) (flags OFF, no `.env` change).

### 1.2 Verify on production host (read-only)

**Git dubious ownership:** use per-invocation `safe.directory` — **not** `git config --global`.

Script (recommended after `git pull` on prod):

```bash
bash /var/www/mywave/automation/production/phase2_preflight_readonly.sh | tee /tmp/prod_phase2_preflight.log
```

**PASS:** stdout ends with `PREFLIGHT_OK`.

Manual (same checks):

```bash
cd /var/www/mywave
GIT="git -c safe.directory=/var/www/mywave"
sudo -u www-data $GIT -C /var/www/mywave fetch origin main
sudo -u www-data $GIT -C /var/www/mywave rev-parse HEAD
sudo -u www-data $GIT -C /var/www/mywave log -1 --oneline
sudo -u www-data $GIT -C /var/www/mywave rev-parse origin/main
sudo -u www-data $GIT -C /var/www/mywave merge-base --is-ancestor 27f2d8869ddb269f09e081aa7d10694fb65ee844 HEAD \
  && echo "PASS: HEAD >= rollout baseline 27f2d886" \
  || echo "FAIL: deploy main to 27f2d886+ before Step 1"
```

**Duplicate `.env` keys:** Flask/load_dotenv typically **last key wins**. Pre-flight prints all `SPREADSHEET_ID` / `GOOGLE_CALENDAR_ID` lines + effective value. Dedupe `.env` is recommended **before Step 1** (separate maintenance; not during read-only pre-flight).

If behind on HEAD: deploy code **with flags still OFF**, smoke Phase 1, **then** proceed to flag rollout (separate GM approval).

---

## 2. Backup commands (mandatory before any `.env` change)

### 2.1 Automated project backup

```bash
sudo MYWAVE_ROOT=/var/www/mywave \
  BACKUP_ROOT=/var/backups/mywave \
  BACKUP_KEEP_DAYS=7 \
  bash /var/www/mywave/deploy/scripts/backup_mywave.sh
```

**Output:** `/var/backups/mywave/YYYYMMDD-HHMM/` containing `project/`, `.env.backup`, SQLite DB copies, `instance_service_account.json.backup` (if present).

### 2.2 Manual `.env` snapshot (rollout-specific)

```bash
TS="$(date +%Y%m%d_%H%M%S)"
cp -a /var/www/mywave/.env "/var/backups/mywave/.env.pre_phase2_${TS}"
chmod 600 "/var/backups/mywave/.env.pre_phase2_${TS}"
ls -la "/var/backups/mywave/.env.pre_phase2_${TS}"
```

### 2.3 Record current production state

```bash
cd /var/www/mywave
sudo -u www-data git rev-parse HEAD | tee "/var/backups/mywave/head.pre_phase2_${TS}.txt"
grep -E '^(GOOGLE_CALENDAR_ID|SPREADSHEET_ID|GUNICORN_BIND|SERVER_NAME|BOOKING_PHASE2_)' .env \
  | tee "/var/backups/mywave/env_booking.pre_phase2_${TS}.txt"
sudo systemctl is-active mywave-site | tee "/var/backups/mywave/mywave-site.active.pre_phase2_${TS}.txt"
curl -fsS https://mywavewake.ru/health | tee "/var/backups/mywave/health.pre_phase2_${TS}.json"
```

---

## 3. Verify production `.env` has no Phase 2 flags (pre-condition)

```bash
cd /var/www/mywave

# Must return nothing OR explicit =0
grep -E '^BOOKING_PHASE2_' .env || echo "OK: no BOOKING_PHASE2_* lines in .env"

# Confirm prod Google resources (do NOT change)
grep -E '^(GOOGLE_CALENDAR_ID|SPREADSHEET_ID)=' .env | tail -2
```

**Expected before rollout:**

| Check | Expected |
|-------|----------|
| `BOOKING_PHASE2_*` | absent or all `=0` |
| `SPREADSHEET_ID` | production booking sheet `1kyNQVjeLLe4Ra6oWuf84fHqSjUlWXI8MakVMOrCgic0` (verify tail on server) |
| `GOOGLE_CALENDAR_ID` | production calendar (read from `.env` — **not** staging `e4ab…`) |
| Staging IDs | **must NOT appear** in `/var/www/mywave/.env` |

**Blocklist guard (staging must not leak to prod):**

```bash
grep -E '16Ewm8Npv3bkNH37X-KAm3PWmRedQ1a8xoiO6LPggyBI|e4ab0adc25a259eebdf83a506073dd5874dee79890b038f924f164703d187dec' .env \
  && echo "FAIL: staging resource ID in prod .env" \
  || echo "OK: no staging Sheet/Calendar in prod .env"
```

---

## 4. Full list of Phase 2 flags

| Flag | Default (code) | Depends on | Effect when ON |
|------|------------------|------------|----------------|
| `BOOKING_PHASE2_AVAILABILITY` | `0` | — | GET slots from **Google Calendar**; POST pipeline **recheck** before write; idempotency range check |
| `BOOKING_PHASE2_TRAVEL_BUFFER` | `0` | `AVAILABILITY=1` | 120 min buffer gym ↔ boat in availability engine |
| `BOOKING_PHASE2_MULTI_SET_BOAT` | `0` | — (slots need AVAILABILITY for Calendar grid) | Boat `max_set_count` in slots API; continuous N×30 min events |
| `BOOKING_PHASE2_SUMMARY_V2` | `0` | — | New bookings: summary `Тренировка — Зал/Катер — … (WEB_ID: …)` |
| `BOOKING_PHASE2_GYM_LOCATION_V2` | `0` | — | New gym events: location `Зал` (v2 venue contract) |

**Target state (full Phase 2):**

```bash
BOOKING_PHASE2_AVAILABILITY=1
BOOKING_PHASE2_TRAVEL_BUFFER=1
BOOKING_PHASE2_MULTI_SET_BOAT=1
BOOKING_PHASE2_SUMMARY_V2=1
BOOKING_PHASE2_GYM_LOCATION_V2=1
```

**Code reference:** `app/config/booking_features.py` — `TRAVEL_BUFFER` is ignored unless `AVAILABILITY=1`.

---

## 5. Rollout strategy

### 5.1 Recommended: controlled stepped rollout (5 steps)

Each step: set flag(s) → restart **only** `mywave-site` → run smoke §7 → **monitor 30–60 min** (§9) → GM go/no-go for next step.

| Step | Flags set to `1` | Restart | Primary risk | Smoke focus |
|------|------------------|---------|--------------|-------------|
| **0** | (none) | no | — | Pre-flight §3, §6 |
| **1** | `BOOKING_PHASE2_AVAILABILITY` | yes | Slots source switches Calendar; POST recheck | `/health`, slots API boat+gym, read-only grid |
| **2** | + `BOOKING_PHASE2_TRAVEL_BUFFER` | yes | Buffer may hide slots | Buffer read-only check (§7.4) |
| **3** | + `BOOKING_PHASE2_MULTI_SET_BOAT` | yes | Multi-set range blocking | `max_set_count` in boat slots (§7.5) |
| **4** | + `BOOKING_PHASE2_SUMMARY_V2` | yes | New event title format | Test booking → Calendar summary (§7.6) |
| **5** | + `BOOKING_PHASE2_GYM_LOCATION_V2` | yes | Gym location label | Test gym booking → location `Зал` (§7.6) |

**Why stepped:** isolates failure domain; aligns with `BOOKING_PHASE2_STAGING_SMOKE.md` §10.

### 5.2 Alternative: controlled bundle (1 restart)

If GM accepts higher blast radius (staging validated **all flags ON together**):

```bash
# After backup §2 — append all five flags at once, single restart, full smoke §7
```

Use only when maintenance window is short and on-call is available for immediate rollback §8.

### 5.3 Order constraints

1. **Never** set `BOOKING_PHASE2_TRAVEL_BUFFER=1` without `BOOKING_PHASE2_AVAILABILITY=1` (code ignores buffer otherwise).
2. `SUMMARY_V2` and `GYM_LOCATION_V2` may be enabled in **one step** (step 4+5 combined) — both affect writer only on **new** bookings.
3. **Do not** change `GOOGLE_CALENDAR_ID`, `SPREADSHEET_ID`, or TGbotAdmin config during flag rollout.

### 5.4 Pre-rollout code deploy (if HEAD behind)

```bash
sudo MYWAVE_ROOT=/var/www/mywave bash /var/www/mywave/deploy/scripts/backup_mywave.sh

cd /var/www/mywave
sudo -u www-data git fetch origin main
sudo -u www-data git checkout main
sudo -u www-data git pull --ff-only origin main
sudo -u www-data git rev-parse HEAD

source venv/bin/activate
export SECRET_KEY="$(grep -E '^SECRET_KEY=' .env | tail -1 | cut -d= -f2-)"

python -m pytest tests/unit/test_booking_grid.py \
  tests/unit/test_booking_pipeline_phase2.py \
  tests/unit/test_booking_availability_phase2.py \
  tests/unit/test_booking_calendar_v2.py \
  tests/unit/test_booking_sheets_compensation.py \
  tests/unit/test_booking_features.py \
  tests/unit/test_booking_phase1.py \
  tests/unit/test_boat_slots.py -q

sudo systemctl restart mywave-site
sleep 8
curl -fsS https://mywavewake.ru/health
```

**Expected pytest:** `87 passed` (booking suite).

### 5.5 Optional pre-flag Telegram smoke (caveat closure)

If GM wants maximum confidence before step 1:

1. TGbotAdmin creates **one** test booking on **production** calendar (existing bot path, `(ID: tg_id)`).
2. Site read-only: verify slots API reflects occupancy; no WEB_ID false duplicate.
3. Document event ID; cancel after test if policy allows.

**Not required** for rollout approval per GM caveat acceptance.

---

## 6. Exact production commands (per flag step)

**Variables for all steps:**

```bash
export PROD_ROOT=/var/www/mywave
export PROD_URL=https://mywavewake.ru
export TS="$(date +%Y%m%d_%H%M%S)"
cd "$PROD_ROOT"
```

### 6.1 Helper: append or update flag in `.env`

```bash
set_flag() {
  local key="$1" val="$2"
  if grep -qE "^${key}=" .env; then
    sed -i "s/^${key}=.*/${key}=${val}/" .env
  else
    echo "${key}=${val}" >> .env
  fi
}
```

### 6.2 Step 1 — `BOOKING_PHASE2_AVAILABILITY=1`

```bash
cd /var/www/mywave
cp -a .env "/var/backups/mywave/.env.step1_availability_${TS}"

set_flag BOOKING_PHASE2_AVAILABILITY 1
# Ensure others still off unless already stepped
set_flag BOOKING_PHASE2_TRAVEL_BUFFER 0
set_flag BOOKING_PHASE2_MULTI_SET_BOAT 0
set_flag BOOKING_PHASE2_SUMMARY_V2 0
set_flag BOOKING_PHASE2_GYM_LOCATION_V2 0

grep -E '^BOOKING_PHASE2_' .env

sudo systemctl restart mywave-site
sleep 8
sudo systemctl is-active mywave-site
curl -fsS "${PROD_URL}/health" | python3 -m json.tool
```

### 6.3 Step 2 — add `BOOKING_PHASE2_TRAVEL_BUFFER=1`

```bash
cd /var/www/mywave
cp -a .env "/var/backups/mywave/.env.step2_travel_buffer_${TS}"

set_flag BOOKING_PHASE2_TRAVEL_BUFFER 1
grep -E '^BOOKING_PHASE2_' .env

sudo systemctl restart mywave-site
sleep 8
curl -fsS "${PROD_URL}/health" | python3 -m json.tool
```

### 6.4 Step 3 — add `BOOKING_PHASE2_MULTI_SET_BOAT=1`

```bash
cd /var/www/mywave
cp -a .env "/var/backups/mywave/.env.step3_multi_set_${TS}"

set_flag BOOKING_PHASE2_MULTI_SET_BOAT 1
grep -E '^BOOKING_PHASE2_' .env

sudo systemctl restart mywave-site
sleep 8
curl -fsS "${PROD_URL}/health" | python3 -m json.tool
```

### 6.5 Step 4 — add `BOOKING_PHASE2_SUMMARY_V2=1`

```bash
cd /var/www/mywave
cp -a .env "/var/backups/mywave/.env.step4_summary_v2_${TS}"

set_flag BOOKING_PHASE2_SUMMARY_V2 1
grep -E '^BOOKING_PHASE2_' .env

sudo systemctl restart mywave-site
sleep 8
curl -fsS "${PROD_URL}/health" | python3 -m json.tool
```

### 6.6 Step 5 — add `BOOKING_PHASE2_GYM_LOCATION_V2=1` (final)

```bash
cd /var/www/mywave
cp -a .env "/var/backups/mywave/.env.step5_gym_location_v2_${TS}"

set_flag BOOKING_PHASE2_GYM_LOCATION_V2 1
grep -E '^BOOKING_PHASE2_' .env

sudo systemctl restart mywave-site
sleep 8
curl -fsS "${PROD_URL}/health" | python3 -m json.tool
```

### 6.7 Bundle fast-path (all flags, single restart)

```bash
cd /var/www/mywave
cp -a .env "/var/backups/mywave/.env.bundle_all_phase2_${TS}"

set_flag BOOKING_PHASE2_AVAILABILITY 1
set_flag BOOKING_PHASE2_TRAVEL_BUFFER 1
set_flag BOOKING_PHASE2_MULTI_SET_BOAT 1
set_flag BOOKING_PHASE2_SUMMARY_V2 1
set_flag BOOKING_PHASE2_GYM_LOCATION_V2 1
grep -E '^BOOKING_PHASE2_' .env

sudo systemctl restart mywave-site
sleep 8
curl -fsS https://mywavewake.ru/health | python3 -m json.tool
```

### 6.8 Forbidden commands

```bash
# DO NOT RUN during Phase 2 flag rollout:
sudo systemctl restart mywave-node.service
sudo systemctl restart mywave-telegram-bot.service
# Do not edit TGbotAdmin production config
# Do not point prod .env to staging Calendar/Sheet IDs
```

---

## 7. Smoke checks after each flag step

**Smoke date:** pick a **future** date with low real traffic (e.g. `+7..+14 days`, Saturday for gym schedule).  
Replace `SMOKE_DATE` below. **Do not use staging dates** (`2026-06-12/13/27`) on prod unless they are still in the future and approved.

```bash
export PROD_URL=https://mywavewake.ru
export SMOKE_DATE=2026-06-21   # CHANGE: future prod-safe date
```

### 7.1 `/health` (every step)

```bash
curl -fsS "${PROD_URL}/health" | python3 -m json.tool
```

**PASS:**

- HTTP `200`
- `status` is `ok` or `degraded` (not `unhealthy`)
- `database` OK
- `google` OK (required for booking)

### 7.2 Public routes (every step)

```bash
curl -fsS -o /dev/null -w "home %{http_code}\n" "${PROD_URL}/"
curl -fsS -o /dev/null -w "robots %{http_code}\n" "${PROD_URL}/robots.txt"
```

**PASS:** `200` for both.

### 7.3 `/api/calendar/slots` — boat grid (step 1+)

```bash
curl -fsS "${PROD_URL}/api/calendar/slots/${SMOKE_DATE}?service=boat" \
  | python3 -c "
import json,sys
d=json.load(sys.stdin)
times=[x.get('time') for x in d] if isinstance(d,list) else []
print('count', len(times))
print('first', times[0] if times else None)
print('last', times[-1] if times else None)
"
```

**PASS (Phase 2 boat grid):**

- `count` **26** (typical full grid)
- `first` **`07:00`**
- `last` **`19:30`**
- No slots `06:00` / `20:00`

### 7.4 `/api/calendar/slots` — gym capacity (step 1+)

```bash
curl -fsS "${PROD_URL}/api/calendar/slots/${SMOKE_DATE}?service=gym" \
  | python3 -c "
import json,sys
d=json.load(sys.stdin)
for row in (d if isinstance(d,list) else [])[:5]:
    print(row.get('time'), 'available', row.get('available'), 'remaining', row.get('remaining'))
"
```

**PASS:**

- Response is non-empty list on scheduled gym days
- Rows include `remaining` (0–4) when Phase 2 availability active
- Full slots: `available=false` or omitted per API contract

### 7.5 Travel buffer read-only (step 2+)

After a **known** gym or boat event exists on `SMOKE_DATE`, verify blocked adjacent service slots (same logic as staging S5). Prefer **read-only** slot inspection; only create anchor bookings in approved maintenance window.

**PASS pattern:** cross-service slots inside 120 min travel window blocked in slots API.

### 7.6 Multi-set boat (step 3+)

```bash
curl -fsS "${PROD_URL}/api/calendar/slots/${SMOKE_DATE}?service=boat" \
  | python3 -c "
import json,sys
d=json.load(sys.stdin)
for row in (d if isinstance(d,list) else []):
    if row.get('time')=='07:00':
        print('max_set_count', row.get('max_set_count'))
        break
"
```

**PASS:** `max_set_count` present and `>= 1` on available boat rows.

### 7.7 Test booking + conflict `409` (steps 4–5 / final)

**Only in GM-approved window.** Use test name/phone; prefer off-peak slot.

```bash
cd /var/www/mywave
source venv/bin/activate
export SECRET_KEY="$(grep -E '^SECRET_KEY=' .env | tail -1 | cut -d= -f2-)"

python3 <<'PY'
import os, sys
sys.path.insert(0, "/var/www/mywave")
os.chdir("/var/www/mywave")
from app import create_app
app = create_app()
c = app.test_client()
csrf = c.get("/api/csrf-token").get_json()["csrf_token"]
# CHANGE: date/time/phone — prod test slot only
payload = {
    "date": os.environ.get("SMOKE_DATE", "2026-06-21"),
    "time": "13:00",
    "name": "Phase2 Prod Smoke",
    "phone": "+79990001122",
    "service_type": "boat",
    "set_count": 1,
}
r1 = c.post("/api/calendar/book", json=payload, headers={"X-CSRFToken": csrf})
print("book1", r1.status_code, r1.get_json())
r2 = c.post("/api/calendar/book", json=payload, headers={"X-CSRFToken": csrf})
print("book2", r2.status_code, r2.get_json())
PY
```

**PASS:**

- First POST: `200` or `201`
- Second POST (same slot): **`409`** with boat occupied / slot unavailable message
- **No orphan:** Workouts row has Client_Workouts counterpart (§7.8)

### 7.8 Calendar / Sheets verification (after test booking)

**Calendar (production ID from `.env`):**

- New event exists at booked time
- Step 4+: summary matches v2 (`Тренировка — Катер — … (WEB_ID: …)`)
- Step 5+: gym booking location `Зал`

**Sheets** (`SPREADSHEET_ID=1kyNQVjeLLe4Ra6oWuf84fHqSjUlWXI8MakVMOrCgic0`):

- `Workouts` row: `workout_id` = Calendar `event.id`
- `Client_Workouts` row: status `подтверждено`
- `orphan_count` check (optional on prod):

```bash
cd /var/www/mywave
source venv/bin/activate
export SECRET_KEY="$(grep -E '^SECRET_KEY=' .env | tail -1 | cut -d= -f2-)"
# Prod orphan script: run only if/when automation/staging/s9 adapted for prod guard
# Manual: verify Workouts vs Client_Workouts in Sheet UI
```

### 7.9 Flags OFF regression (after full rollout, optional)

Clone flags to `0`, restart, confirm Phase 1 slots behavior — **only** in dedicated rollback drill, not in production during live window.

---

## 8. Rollback commands

### 8.1 Flag rollback (preferred — keeps code, restores Phase 1 behavior)

```bash
cd /var/www/mywave
TS="$(date +%Y%m%d_%H%M%S)"
cp -a .env "/var/backups/mywave/.env.rollback_${TS}"

set_flag() {
  local key="$1" val="$2"
  if grep -qE "^${key}=" .env; then
    sed -i "s/^${key}=.*/${key}=${val}/" .env
  else
    echo "${key}=${val}" >> .env
  fi
}

set_flag BOOKING_PHASE2_AVAILABILITY 0
set_flag BOOKING_PHASE2_TRAVEL_BUFFER 0
set_flag BOOKING_PHASE2_MULTI_SET_BOAT 0
set_flag BOOKING_PHASE2_SUMMARY_V2 0
set_flag BOOKING_PHASE2_GYM_LOCATION_V2 0

grep -E '^BOOKING_PHASE2_' .env

sudo systemctl restart mywave-site
sleep 8
curl -fsS https://mywavewake.ru/health | python3 -m json.tool
```

**Or restore exact pre-rollout file:**

```bash
cp -a "/var/backups/mywave/.env.pre_phase2_YYYYMMDD_HHMMSS" /var/www/mywave/.env
sudo systemctl restart mywave-site
```

### 8.2 Rollback verification

```bash
curl -fsS https://mywavewake.ru/health
curl -fsS "https://mywavewake.ru/api/calendar/slots/${SMOKE_DATE}?service=boat" | python3 -m json.tool | head
sudo journalctl -u mywave-site --since "10 min ago" --no-pager | tail -50
```

**PASS:** health OK; booking UI/API behaves as Phase 1; no new Phase 2 log markers on slots path.

### 8.3 Code rollback (only if bad deploy — not flag-only issue)

```bash
cd /var/www/mywave
PREV="<previous_known_good_sha>"   # e.g. document before rollout
sudo systemctl stop mywave-site
sudo -u www-data git checkout "$PREV"
sudo systemctl start mywave-site
curl -fsS https://mywavewake.ru/health
```

**Note:** Existing Calendar events created under Phase 2 remain valid; no DB migration rollback required.

### 8.4 Rollback triggers (GM)

- `/health` not `200` or `unhealthy` > 5 min after restart
- Booking POST 5xx rate increase
- Widespread empty slots API with Calendar up
- `booking_sheets_partial_failure` without successful compensation
- TGbotAdmin reports parser/regression on live calendar

---

## 9. Monitoring window (30–60 min per step; 24h after final step)

### 9.1 systemd / app logs

```bash
sudo journalctl -u mywave-site -f
sudo journalctl -u mywave-site --since "30 min ago" --no-pager | tail -200
```

### 9.2 Booking pipeline markers (grep)

```bash
sudo journalctl -u mywave-site --since "1 hour ago" --no-pager \
  | grep -E 'booking_pipeline_ok|booking_slot_unavailable|booking_recheck_blocked|availability_blocked_travel_buffer|booking_calendar_event_created|booking_sheets_partial_failure|booking_sheets_compensation|Slots API|slots_request' \
  | tail -80
```

| Log event | Meaning |
|-----------|---------|
| `booking_pipeline_ok` | Successful booking |
| `booking_slot_unavailable` / `booking_recheck_blocked` | Expected 409 path |
| `availability_blocked_travel_buffer` | Travel buffer working |
| `booking_calendar_event_created` | Calendar write OK |
| `booking_sheets_partial_failure` | **Alert** — partial Sheets write |
| `compensation` / `workout_row_mark_failed` | Compensation path — verify no orphan |

### 9.3 Google API errors

```bash
sudo journalctl -u mywave-site --since "1 hour ago" --no-pager \
  | grep -iE 'google|sheets|calendar|403|429|502|SSL|dns' | tail -50
```

### 9.4 Health cron (existing)

```bash
# scripts/healthcheck.sh — should remain passing
grep mywave-healthcheck /var/log/syslog | tail -5
```

### 9.5 Metrics (if Prometheus enabled)

- HTTP 5xx rate on `/api/calendar/*`
- Booking error responses (409 expected; 500 not)

### 9.6 Human checks (first 24h after full rollout)

- [ ] 1 real boat booking (or test) — Calendar + Sheets
- [ ] 1 real gym booking — capacity decrement
- [ ] TGbotAdmin: no false duplicate on WEB_ID events
- [ ] No customer reports of empty schedule

---

## 10. Explicit guardrails

| Rule | Status |
|------|--------|
| Change production `.env` `BOOKING_PHASE2_*` | **Only after separate GM approval** |
| Restart `mywave-site` | **Allowed** (required per flag step) |
| Restart `mywave-node.service` | **FORBIDDEN** |
| Restart `mywave-telegram-bot.service` | **FORBIDDEN** |
| Touch TGbotAdmin production | **FORBIDDEN** |
| Change `GOOGLE_CALENDAR_ID` / `SPREADSHEET_ID` on prod | **FORBIDDEN** during flag rollout |
| Use staging Sheet `16Ewm8…` or staging Calendar `e4ab…` on prod | **FORBIDDEN** |
| Run staging scripts (`automation/staging/*`) against prod `.env` | **FORBIDDEN** (blocklist in `_staging_env.py`) |

---

## 11. GM approval checklist (before execution)

- [ ] Staging **GREEN WITH CAVEAT** accepted (S5/S8/S9/S7)
- [ ] Production HEAD ≥ `27f2d886`
- [ ] Pre-flight §3: prod flags OFF, prod IDs confirmed
- [ ] Backup §2 completed
- [ ] Rollout strategy chosen: stepped §5.1 **or** bundle §5.2
- [ ] Maintenance window + on-call assigned
- [ ] Rollback file path recorded
- [ ] Optional: Telegram targeted smoke §5.5
- [ ] **Separate written GM approval** to execute §6

**Until checklist complete:** §6 commands are **documentation only** — **do not execute**.

---

## 12. References

| Document | Purpose |
|----------|---------|
| [`BOOKING_PHASE2_STAGING_E2E_REPORT_2026-06-07.md`](BOOKING_PHASE2_STAGING_E2E_REPORT_2026-06-07.md) | Staging close-out evidence |
| [`BOOKING_PHASE2_TGBOTADMIN_S7_HANDOFF.md`](BOOKING_PHASE2_TGBOTADMIN_S7_HANDOFF.md) | S7 handoff |
| [`BOOKING_PHASE2_STAGING_SMOKE.md`](BOOKING_PHASE2_STAGING_SMOKE.md) | Full smoke matrix |
| [`BOOKING_CALENDAR_EVENT_CONTRACT_v2.md`](BOOKING_CALENDAR_EVENT_CONTRACT_v2.md) | Event format |
| [`BOOKING_AVAILABILITY_CONTRACT_v1.md`](BOOKING_AVAILABILITY_CONTRACT_v1.md) | Availability rules |
| [`BOOKING_PHASE2_SHEETS_COMPENSATION_PACKAGE.md`](BOOKING_PHASE2_SHEETS_COMPENSATION_PACKAGE.md) | Compensation logs |
| [`docs/deployment/PRODUCTION_STACK.md`](../deployment/PRODUCTION_STACK.md) | Prod stack |
| `deploy/scripts/backup_mywave.sh` | Backup script |
| `app/config/booking_features.py` | Flag definitions |

---

## 13. Final recommendation

| Question | Answer |
|----------|--------|
| Staging gate | **GREEN WITH CAVEAT** — ready for prod **planning** |
| Execute prod flags now? | **NO** — await separate GM approval |
| Recommended execution | Stepped rollout §5.1 after approval |
| Prod rollout ready after approval? | **YES** — package complete |

**Site statement:** Staging checks and TGbotAdmin S7 read-only audit support proceeding to **GM approval gate** for production `BOOKING_PHASE2_*`. Production remains **untouched** until explicit approval.
