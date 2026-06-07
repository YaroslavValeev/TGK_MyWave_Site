# BOOKING Phase 2 — Staging E2E Report

**Date:** 2026-06-07 (initial) · **Close-out revision:** 2026-06-08  
**Author:** Site MyWave  
**Audience:** GM / Owner / TGbotAdmin  
**GM decision (2026-06-08):** **NO / BLOCKED FOR PROD FLAGS ON** (unchanged until S7 PASS)  
**Status:** **SITE STAGING CLOSE-OUT: PASS (S5 / S8 / S9)** — Phase 2 staging gate **open pending S7**

**Report revision:** 2026-06-08 — S5/S8/S9 close-out PASS on HEAD `1ecbd161`; S7 pending TGbotAdmin.

---

## 1. Environment snapshot

| Field | Value |
|-------|--------|
| **Staging root** | `/var/www/mywave-staging` |
| **Git HEAD** | `1ecbd161` |
| **Commit message** | `fix(staging): S5 Part A idempotent re-run on clean date` |
| **Base URL** | `http://127.0.0.1:5002` |
| **systemd unit** | `mywave-staging.service` |
| **Health** | `degraded` — **database OK**, **google OK**; optional ai_gateway/sentry off |
| **Prod touched** | **No** — prod `.env` flags OFF; prod services not restarted |

### 1.1 Google resources (staging only)

| Resource | Full ID | Tail (evidence) |
|----------|---------|-----------------|
| **Calendar** | `e4ab0adc25a259eebdf83a506073dd5874dee79890b038f924f164703d187dec@group.calendar.google.com` | `…187dec@group.calendar.google.com` |
| **Calendar name** | StagingMyWave | — |
| **Spreadsheet** | `16Ewm8Npv3bkNH37X-KAm3PWmRedQ1a8xoiO6LPggyBI` | `16Ew…ggyBI` |
| **SA** | `mywavetg@rock-sublime-445613-t2.iam.gserviceaccount.com` | Editor on staging Calendar + Sheet |

### 1.2 Phase 2 flags (staging `.env`)

```text
BOOKING_PHASE2_AVAILABILITY=1
BOOKING_PHASE2_TRAVEL_BUFFER=1
BOOKING_PHASE2_MULTI_SET_BOAT=1
BOOKING_PHASE2_SUMMARY_V2=1
BOOKING_PHASE2_GYM_LOCATION_V2=1
```

### 1.3 Infra notes

- `GUNICORN_BIND=127.0.0.1:5002` (prod `mywave-site` uses `:5000`)
- `DATABASE_URL=sqlite:////var/www/mywave-staging/instance/mywave.db`
- `Schedule` sheet seeded (6 rows) — required for gym slots API
- DNS `staging.mywavewake.ru` — **not ready** (NXDOMAIN); smoke via localhost

---

## 2. Smoke matrix S1–S9

**Smoke date:** `2026-06-12`  
**Method:** API scripts + CSRF session (`POST /api/calendar/book`)

| ID | Expected | Actual | Evidence | Result |
|----|----------|--------|----------|--------|
| **S1** | Boat 1 set 30 min; summary v2; 2nd client same slot → **409** | 1st POST **201** (`13:00`); 2nd POST **409** «слот на катере уже занят» | `S1_ok`; workout_id tail `…qgan5c` | **PASS** |
| **S2** | Boat `set_count=3`; 90 min continuous; summary «3 сета»; blocks adjacent range | POST **201** at `07:00`, `set_count=3` | `S2_ok`; workout_id tail `…050p9qc` | **PASS** |
| **S3** | Boat grid first `07:00`, last `19:30`, count **26** | `count 26 first 07:00 last 19:30 grid_ok` | `/api/calendar/slots/2026-06-12?service=boat` | **PASS** |
| **S4** | Gym `remaining` 4→0; 4× **201**; 5th → **409** | 4× **201** at `16:00`; 5th **409** after `sleep 3` («нет свободных мест») | `S4_ok`; 5th burst got **502** (rate limit) — retried PASS | **PASS** |
| **S5** | Boat 12:00 → gym before 14:30 blocked, 14:30 OK; gym 10:00 → boat before 13:30 blocked, 13:30 OK | Part B `2026-06-13`: `book_gym_10 201`, `boat_12_blocked True`, `boat_1330_available True`. Part A `2026-06-27`: `book_boat_12 201`, `gym_14_blocked True`, `gym_1430_available True`. `S5_ok` | `/tmp/s5_final.log` — run **2026-06-08 ~01:59 MSK** @ `1ecbd161` | **PASS** |
| **S6** | Race: one **201**, one **409**; no orphan | `10:30`: A **201**, B **409** | `S6_ok 10:30` | **PASS** |
| **S7** | WEB `(WEB_ID: bk_…)` vs TG `(ID: …)`; no false duplicate; TGbotAdmin parser OK | **Not executed** | Awaiting TGbotAdmin joint smoke on staging calendar | **FAIL / PENDING** |
| **S8** | Calendar: boat `07:00` 90 min / «Катер» / 3 sets; gym `16:00` 90 min / «Зал» / summary v2 | `"s8_pass": true`, `S8_ok`; boat `07:00` duration 90, location `Катер`, `set_count=3`; gym `16:00` duration 90, location `Зал` | `/tmp/s8_calendar.json` (script `s8_calendar_dump.py`, date `2026-06-12`) | **PASS** |
| **S9** | `orphan_count 0` after smokes | `orphan_count 0` / `S9_ok` on staging Sheet `16Ewm8Npv3bkNH37X-KAm3PWmRedQ1a8xoiO6LPggyBI` | `/tmp/s9_final.log` — run **2026-06-08 ~01:59 MSK** | **PASS** |

### 2.1 Optional / out of scope

| ID | Note |
|----|------|
| S10 | Flags OFF regression — not run on staging (prod remains Phase 1) |

---

## 3. Unit tests

| Check | Result |
|-------|--------|
| Booking unit suite (87 tests) | **87 passed** |
| Command | `BOOKING_PHASE2_*=0 ENABLE_GOOGLE_SERVICES=0 python -m pytest tests/unit/test_booking_*.py …` |
| Note | Staging `.env` has flags ON; explicit `=0` required until `tests/conftest.py` isolation merged |

---

## 4. Google Sheets evidence (Owner accepted 2026-06-07)

**Source:** Owner screenshots — staging spreadsheet **MyWave Staging Booking**  
**Spreadsheet ID:** `16Ewm8Npv3bkNH37X-KAm3PWmRedQ1a8xoiO6LPggyBI`  
**GM status:** **Accepted** as Sheets-layer / journal contract evidence.

### 4.1 What this evidence closes

| Area | Status | Notes |
|------|--------|-------|
| Sheets contract (headers + tabs) | **Accepted** | `Clients`, `Workouts`, `Client_Workouts`, `Schedule` |
| Staging Schedule seeded | **Accepted** | Gym slot grid present |
| Gym capacity rows | **Accepted** | `max_capacity=4` per schedule row |
| Boat/gym duration + location in Sheets | **Accepted** | boat 30/90 min `Катер`; gym 90 min `Зал` |
| Client_Workouts linkage | **Accepted** | Matching rows; status `подтверждено` |
| S9 orphan check (visual support) | **Accepted** | Every Workout row has Client_Workouts counterpart |
| Calendar → Sheets write path | **Accepted** | Post-smoke journal rows match API bookings |

### 4.2 What this evidence does NOT close

| Area | Status | Notes |
|------|--------|-------|
| **S8 Calendar UI sign-off** | **Still pending** | Sheets §4 ≠ Calendar; need event details (§6) |
| Summary v2 in Calendar event title | **Pending** | Requires Calendar UI or Calendar API export |
| Event start/end/duration in Calendar | **Pending** | e.g. boat 07:00–08:30 (90 min) |
| Extended properties (`set_count`) in Calendar | **Pending** | Calendar API or UI evidence |

### 4.3 Schedule tab (accepted)

Columns: `day_of_week`, `time`, `max_capacity`

| day_of_week | time | max_capacity |
|-------------|------|--------------|
| friday | 10:00 | 4 |
| friday | 15:00 | 4 |
| friday | 16:00 | 4 |
| friday | 17:00 | 4 |
| saturday | 10:00 | 4 |
| saturday | 15:00 | 4 |

### 4.4 Clients tab (accepted — staging test data)

| name | source | status |
|------|--------|--------|
| Staging Boat A | web | new |
| Gym 1 … Gym 4 | web | new |
| Staging Boat 3set | web | new |
| Race A | web | new |

### 4.5 Workouts tab (accepted — aligns with smoke 2026-06-12)

| date | time | duration (min) | location | workout_type | workout_status | current_capacity |
|------|------|----------------|----------|--------------|----------------|------------------|
| 2026-06-12 | 12:00 | 30 | Катер | boat | active | 1 |
| 2026-06-12 | 13:00 | 30 | Катер | boat | active | 1 |
| 2026-06-12 | 16:00 | 90 | Зал | gym | active | 1 (×4 rows) |
| 2026-06-12 | 07:00 | 90 | Катер | boat | active | 1 |
| 2026-06-12 | 11:00 | 30 | Катер | boat | active | 1 |
| 2026-06-12 | 10:30 | 30 | Катер | boat | active | 1 |

Mapping to smoke:

- S1 → boat `13:00` 30 min
- S2 → boat `07:00` 90 min (3 sets)
- S4 → gym `16:00` ×4, 90 min each
- S6 → boat `10:30` 30 min

### 4.6 Client_Workouts tab (accepted)

- Matching `client_id` / `workout_id` pairs for all staging Workouts rows above
- Status column: **`подтверждено`**
- Supports **S9 PASS** together with script `orphan_count 0`

---

## 5. TGbotAdmin verdict (S7)

| Item | Status |
|------|--------|
| Joint smoke on staging calendar | **Not performed** |
| WEB_ID vs ID markers | **Pending** |
| False duplicate check | **Pending** |
| TGbotAdmin Calendar parsing compatibility | **Pending** |

**TGbotAdmin verdict:** _Pending S7 joint/read-only audit — Site staging artifacts ready (§14)._

---

## 6. Calendar evidence & S8 sign-off

**GM status (2026-06-08):** **S8 PASS** (Calendar API dump Variant B)

### 6.1 Owner Calendar screenshots — accepted partially

**Source:** Owner screenshots — Google Calendar **StagingMyWave**

| Confirmed | Detail |
|-----------|--------|
| Calendar connected | `StagingMyWave` visible in Google Calendar |
| Staging events exist | Events present in June 2026 |
| Month view | Event at `07:00` on **`2026-06-12`** visible |
| Owner access | Staging calendar visually accessible |

| Not confirmed on screenshots | Why insufficient for S8 PASS |
|------------------------------|------------------------------|
| Boat `07:00` event details | No popup: summary v2, 90 min, `Катер`, `set_count=3` |
| Gym `16:00` event details | No popup: 90 min, `Зал`, summary v2 |
| Start/end/duration | Not visible on month view |
| Extended properties | `set_count` not shown |

**Excluded from S8 evidence:** day-view screenshot for **`2026-06-08`** with legacy/TGbot-style `(ID: 510686579)` — does not validate Phase 2 web staging contract for `2026-06-12`.

### 6.2 S8 full PASS — required evidence (pick A or B)

#### Variant A — Calendar UI screenshots

Open **`2026-06-12`** in StagingMyWave → event details popup:

| Event | Expected |
|-------|----------|
| Boat `07:00` | Summary v2 «3 сета»; **90 min** (07:00–08:30); location **Катер**; `set_count=3` if shown |
| Gym `16:00` (one of four) | Summary v2; **90 min** (16:00–17:30); location **Зал** |

#### Variant B — Calendar API dump (Site script)

Run on staging host (see §6.3). Required fields per event:

- `summary`, `location`, `start`, `end`, duration (minutes)
- `extendedProperties.private.set_count` (boat multi-set)
- `id`

### 6.3 Calendar API dump (Variant B)

Скрипт: `automation/staging/s8_calendar_dump.py`  
Runbook: [`BOOKING_PHASE2_STAGING_CLOSEOUT_COMMANDS.md`](BOOKING_PHASE2_STAGING_CLOSEOUT_COMMANDS.md) §2.

**S8 PASS when:** JSON `"s8_pass": true` + stdout `S8_ok`.

**Close-out result (2026-06-08):** PASS — evidence file `/tmp/s8_calendar.json` on staging host.

| Event | Expected | Actual (API dump) |
|-------|----------|-------------------|
| Boat `07:00` | 90 min, `Катер`, 3 sets, summary v2 | duration 90, location `Катер`, `set_count=3`, summary contains `WEB_ID:` + «сет» |
| Gym `16:00` | 90 min, `Зал`, summary v2 | duration 90, location `Зал`, summary contains `WEB_ID:` + `Зал` |

### 6.4 S8 checklist (staging, 2026-06-12)

| Event | Expected | Sign-off |
|-------|----------|----------|
| Boat multi-set `07:00` | 90 min, `Катер`, summary v2 «3 сета», `set_count=3` | **PASS** (`s8_calendar.json`) |
| Gym `16:00` | 90 min, `Зал`, summary v2 | **PASS** (`s8_calendar.json`) |
| Boat single `13:00` | 30 min, `(WEB_ID: bk_…)` | Optional |
| Race boat `10:30` | 30 min | Optional |

---

## 7. Orphan audit (S9)

**Close-out run:** 2026-06-08 ~01:59 MSK  
**Evidence:** `/tmp/s9_final.log`  
**Staging Spreadsheet ID (mandatory guard):** `16Ewm8Npv3bkNH37X-KAm3PWmRedQ1a8xoiO6LPggyBI`

```text
s9_spreadsheet_id 16Ewm8Npv3bkNH37X-KAm3PWmRedQ1a8xoiO6LPggyBI
s9_expected_spreadsheet_id 16Ewm8Npv3bkNH37X-KAm3PWmRedQ1a8xoiO6LPggyBI
orphan_count 0
S9_ok
```

Script: `automation/staging/s9_orphan_check.py` — `read_records(Workouts)` vs `Client_Workouts`; no active Workouts without matching Client_Workouts row.

**Supplemental evidence:** Owner Sheets screenshots (§4.6).

---

## 8. Known issues

| # | Issue | Impact | Mitigation |
|---|-------|--------|------------|
| 1 | Staging `.env` copied from prod — duplicate `GOOGLE_CALENDAR_ID` / `SPREADSHEET_ID` lines | Risk of wrong resource on restart | Dedupe script applied / recommended before each restart |
| 2 | Empty `Schedule` tab on first bootstrap | Gym API returned `[]` | Seed 6 schedule rows (friday/saturday) |
| 3 | `GUNICORN_BIND=5000` in copied `.env` | Crash loop vs prod `:5000` | Set `127.0.0.1:5002` |
| 4 | Burst POST / GET → Google **502** | False-negative on 5th booking / slots GET | `sleep 2–3` between calls |
| 5 | pytest with staging `.env` flags ON | 14 failures hitting real Google | Run with `BOOKING_PHASE2_*=0` or conftest fix |
| 6 | `flask db upgrade` eventlet warnings | Noise only | Ignore; migrate completes |
| 7 | Redis greenlet on one-shot Python exit | Noise only | Ignore |
| 8 | `staging.mywavewake.ru` NXDOMAIN | No public HTTPS staging | Use `127.0.0.1:5002` |
| 9 | S5 re-run on polluted dates (409 boat occupied) | False FAIL on repeat close-out | Fixed `1ecbd161`: date `2026-06-27` + idempotent 409 handling |
| 10 | S7 TGbotAdmin joint audit | GM blocker for prod | Handoff §14; [`BOOKING_PHASE2_TGBOTADMIN_S7_HANDOFF.md`](BOOKING_PHASE2_TGBOTADMIN_S7_HANDOFF.md) |

---

## 9. Close-out plan

### 9.1 S5 — full travel buffer PASS ✅ (2026-06-08)

Скрипт: `automation/staging/s5_api_smoke.py` (via `s5_travel_buffer.py`)  
Runbook: [`BOOKING_PHASE2_STAGING_CLOSEOUT_COMMANDS.md`](BOOKING_PHASE2_STAGING_CLOSEOUT_COMMANDS.md) §3.

| Part | Date | Check | Result |
|------|------|-------|--------|
| B gym→boat | `2026-06-13` | gym 10:00 → boat 12:00 blocked, 13:30 allowed | **PASS** |
| A boat→gym | `2026-06-27` | boat 12:00 → gym 14:00 blocked, 14:30 allowed | **PASS** |

**Evidence:** `/tmp/s5_final.log` — `S5_part_B_ok`, `S5_part_A_ok`, `S5_ok` @ HEAD `1ecbd161`, **2026-06-08 ~01:59 MSK**.

### 9.2 S7 — TGbotAdmin joint

1. Point TGbotAdmin to **staging** calendar ID (not prod).
2. One bot booking → verify summary `(ID: tg_user_id)`.
3. One web booking → verify `(WEB_ID: bk_…)`.
4. TGbotAdmin confirms parser does not treat WEB_ID as duplicate of ID.

### 9.3 S8 — Calendar full PASS ✅ (2026-06-08)

Variant B — Calendar API dump. Evidence: `/tmp/s8_calendar.json`, `"s8_pass": true`, `S8_ok`. See §6.3.

---

## 10. Prod rollout guardrails (unchanged)

**Until full S1–S9 PASS + GM approval:**

- Do **not** change production `.env`
- Do **not** enable `BOOKING_PHASE2_*` on production
- Do **not** restart `mywave-site`, `mywave-node.service`, `mywave-telegram-bot.service`
- Do **not** touch TGbotAdmin production config

---

## 11. Final recommendation

| Question | Answer |
|----------|--------|
| Staging contour operational? | **Yes** — `/var/www/mywave-staging`, `127.0.0.1:5002`, HEAD `1ecbd161` |
| Site close-out S5 / S8 / S9? | **Yes — PASS** |
| Core booking smoke (S1–S4, S6)? | **Yes — PASS** (2026-06-12) |
| S7 TGbotAdmin joint audit? | **PENDING** |
| Full Phase 2 staging gate (S1–S9)? | **No** — blocked on S7 only |
| Ready for prod `BOOKING_PHASE2_*` rollout? | **NOT READY** |

**Final recommendation:**

1. **Site staging checks ready for TGbotAdmin S7**
2. **NOT READY for prod rollout until S7 PASS**

Handoff package: [`BOOKING_PHASE2_TGBOTADMIN_S7_HANDOFF.md`](BOOKING_PHASE2_TGBOTADMIN_S7_HANDOFF.md)

---

## 12. References

- Close-out commands: [`BOOKING_PHASE2_STAGING_CLOSEOUT_COMMANDS.md`](BOOKING_PHASE2_STAGING_CLOSEOUT_COMMANDS.md)
- TGbotAdmin S7 handoff: [`BOOKING_PHASE2_TGBOTADMIN_S7_HANDOFF.md`](BOOKING_PHASE2_TGBOTADMIN_S7_HANDOFF.md)
- Bootstrap runbook: [`BOOKING_PHASE2_STAGING_BOOTSTRAP_RUNBOOK.md`](BOOKING_PHASE2_STAGING_BOOTSTRAP_RUNBOOK.md)
- Smoke package: [`BOOKING_PHASE2_STAGING_E2E_PACKAGE.md`](BOOKING_PHASE2_STAGING_E2E_PACKAGE.md)
- Prod deploy baseline: PR #18 @ prod `67b30510` (compensation B+E, flags OFF)

---

## 13. Evidence log (commands run)

```text
# Initial smoke (2026-06-07 / 2026-06-12)
curl -fsS http://127.0.0.1:5002/health                         → degraded, db+google OK
pytest booking suite                                           → 87 passed
S3 grid_ok                                                     → count 26, 07:00–19:30
S1_ok                                                          → 201 + 409 @ 13:00 boat
S2_ok                                                          → 201 @ 07:00 set_count=3
S4_ok                                                          → 4×201 + 409 @ 16:00 gym
S6_ok                                                          → 201 + 409 @ 10:30 boat
Owner Sheets screenshots (2026-06-07)                          → Schedule/Clients/Workouts/Client_Workouts accepted (§4)

# Close-out (2026-06-08, HEAD 1ecbd161)
sudo -u www-data git -C /var/www/mywave-staging reset --hard origin/main  → 1ecbd161
python3 automation/staging/s8_calendar_dump.py                 → s8_pass true, S8_ok → /tmp/s8_calendar.json
python3 automation/staging/s5_api_smoke.py                     → S5_ok → /tmp/s5_final.log (~01:59 MSK)
python3 automation/staging/s9_orphan_check.py                  → orphan_count 0, S9_ok → /tmp/s9_final.log
```

---

## 14. TGbotAdmin S7 handoff (2026-06-08)

**Deliver to TGbotAdmin:**

| # | Item |
|---|------|
| 1 | `/tmp/s8_calendar.json` (copy from staging host) |
| 2 | S5/S8/S9 summary — this report §2, §6.3, §7, §9 + [`BOOKING_PHASE2_TGBOTADMIN_S7_HANDOFF.md`](BOOKING_PHASE2_TGBOTADMIN_S7_HANDOFF.md) |
| 3 | Staging Calendar ID: `e4ab0adc25a259eebdf83a506073dd5874dee79890b038f924f164703d187dec@group.calendar.google.com` |
| 4 | Staging Sheet ID: `16Ewm8Npv3bkNH37X-KAm3PWmRedQ1a8xoiO6LPggyBI` |

**S7 status:** PENDING — TGbotAdmin read-only / joint audit on staging resources only.

**Prod guardrails:** production `.env`, prod `BOOKING_PHASE2_*`, `mywave-site`, `mywave-node.service`, `mywave-telegram-bot.service`, TGbotAdmin prod — **do not touch** until S7 PASS + GM approval.
