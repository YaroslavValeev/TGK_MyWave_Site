# BOOKING Phase 2 — Staging E2E Report

**Date:** 2026-06-07  
**Author:** Site MyWave  
**Audience:** GM / Owner / TGbotAdmin  
**GM decision (2026-06-07):** **NO / BLOCKED FOR PROD FLAGS ON**  
**Status:** **STAGING CONTOUR READY / CORE SMOKE PARTIAL GREEN** (not full Staging GREEN)

**Report revision:** 2026-06-07 — Owner Sheets screenshots accepted (GM ack); Calendar screenshots **partial** (S8 not full PASS).

---

## 1. Environment snapshot

| Field | Value |
|-------|--------|
| **Staging root** | `/var/www/mywave-staging` |
| **Git HEAD** | `8a3febb6d826199e366f607c1ec8d536228d21ab` |
| **Commit message** | `docs(booking): final staging E2E package (PR18 post-deploy)` |
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
| **S5** | Boat 12:00–12:30 → gym before 14:30 blocked; gym 10:00–11:30 → boat before 13:30 blocked | **Partial only:** after boat `13:00`, gym `10:00`/`15:00` `available=false` (buffer); `S5_partial_ok` on `15:00`/`16:00` only | Not executed per canonical S5 times (`12:00` boat / `10:00` gym anchor) | **FAIL / PARTIAL** |
| **S6** | Race: one **201**, one **409**; no orphan | `10:30`: A **201**, B **409** | `S6_ok 10:30` | **PASS** |
| **S7** | WEB `(WEB_ID: bk_…)` vs TG `(ID: …)`; no false duplicate; TGbotAdmin parser OK | **Not executed** | Awaiting TGbotAdmin joint smoke on staging calendar | **FAIL / PENDING** |
| **S8** | Calendar: boat `07:00` 90 min / «Катер» / 3 sets; gym `16:00` 90 min / «Зал» / summary v2 | **Partial:** StagingMyWave connected; month view shows `07:00` on `2026-06-12`; **details not shown** | Owner Calendar screenshots (§6.1) — **API dump or event popup still required** | **PARTIAL / NOT FULL PASS** |
| **S9** | `orphan_count 0` after S1–S6 | `orphan_count 0` / `S9_ok` (post S2, S4, S6) | Script §6 + **Owner Sheets screenshots** (§4) | **PASS** |

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

**TGbotAdmin verdict:** _Awaiting — not ready for sign-off._

---

## 6. Calendar evidence & S8 sign-off

**GM status (2026-06-07):** **S8 PARTIAL / NOT FULL PASS YET**

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

### 6.4 S8 checklist (staging, 2026-06-12)

| Event | Expected | Sign-off |
|-------|----------|----------|
| Boat multi-set `07:00` | 90 min, `Катер`, summary v2 «3 сета», `set_count=3` | **Pending** (partial month view only) |
| Gym `16:00` | 90 min, `Зал`, summary v2 | **Pending** |
| Boat single `13:00` | 30 min, `(WEB_ID: bk_…)` | Optional |
| Race boat `10:30` | 30 min | Optional |

---

## 7. Orphan audit

```text
orphan_count 0
S9_ok
```

Script: `read_records(Workouts)` vs `Client_Workouts` — no active Workouts without matching Client_Workouts row.

**Supplemental evidence:** Owner Sheets screenshots (§4.6) — visual confirmation of Client_Workouts linkage and status `подтверждено`.

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
| 9 | S5 not run per canonical anchor times | GM blocker | See §8.1 close-out plan |
| 10 | S7/S8 Calendar not full PASS | GM blocker | S8: event popup or API dump §6.3; S7: TGbotAdmin |

---

## 9. Close-out plan (to reach full Staging GREEN)

### 9.1 S5 — full travel buffer PASS

Скрипт: `automation/staging/s5_travel_buffer.py`  
Runbook: [`BOOKING_PHASE2_STAGING_CLOSEOUT_COMMANDS.md`](BOOKING_PHASE2_STAGING_CLOSEOUT_COMMANDS.md) §3.

| Part | Date | Check |
|------|------|-------|
| B gym→boat | `2026-06-13` | gym 10:00 → boat 12:00 blocked, 13:30 allowed |
| A boat→gym | `2026-06-20` | boat 12:00 → gym 14:00 blocked, 14:30 allowed |

**PASS:** stdout `S5_ok`.

### 9.2 S7 — TGbotAdmin joint

1. Point TGbotAdmin to **staging** calendar ID (not prod).
2. One bot booking → verify summary `(ID: tg_user_id)`.
3. One web booking → verify `(WEB_ID: bk_…)`.
4. TGbotAdmin confirms parser does not treat WEB_ID as duplicate of ID.

### 9.3 S8 — Calendar full PASS (Variant A or B)

See §6.2–§6.3. **Sheets evidence (§4) does not substitute Calendar sign-off.**

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
| Staging contour operational? | **Yes** — service up, health core OK, staging Calendar/Sheet wired |
| Core booking smoke (S1–S4, S6, S9)? | **Yes — PASS** |
| Sheets layer (Schedule, journal, linkage)? | **Yes — Owner screenshots accepted (§4)** |
| Full Staging GREEN (S1–S9)? | **No** — S5 partial; S7 pending; **S8 partial** |
| Ready for prod `BOOKING_PHASE2_*` rollout? | **NOT READY** |

**Recommendation:** Maintain **STAGING CONTOUR READY / CORE SMOKE PARTIAL GREEN**. Complete S5 (full), S7 (TGbotAdmin), S8 (Calendar sign-off), then resubmit for prod flag approval.

---

## 12. References

- Close-out commands: [`BOOKING_PHASE2_STAGING_CLOSEOUT_COMMANDS.md`](BOOKING_PHASE2_STAGING_CLOSEOUT_COMMANDS.md)
- Bootstrap runbook: [`BOOKING_PHASE2_STAGING_BOOTSTRAP_RUNBOOK.md`](BOOKING_PHASE2_STAGING_BOOTSTRAP_RUNBOOK.md)
- Smoke package: [`BOOKING_PHASE2_STAGING_E2E_PACKAGE.md`](BOOKING_PHASE2_STAGING_E2E_PACKAGE.md)
- Prod deploy baseline: PR #18 @ prod `67b30510` (compensation B+E, flags OFF)

---

## 13. Evidence log (commands run)

```text
sudo -u www-data git -C /var/www/mywave-staging rev-parse HEAD  → 8a3febb6
curl -fsS http://127.0.0.1:5002/health                         → degraded, db+google OK
pytest booking suite                                           → 87 passed
S3 grid_ok                                                     → count 26, 07:00–19:30
S1_ok                                                          → 201 + 409 @ 13:00 boat
S2_ok                                                          → 201 @ 07:00 set_count=3
S4_ok                                                          → 4×201 + 409 @ 16:00 gym
S6_ok                                                          → 201 + 409 @ 10:30 boat
S9_ok                                                          → orphan_count 0
Owner Sheets screenshots (2026-06-07)                          → Schedule/Clients/Workouts/Client_Workouts accepted (§4)
Owner Calendar screenshots (2026-06-07)                        → StagingMyWave partial; S8 not full PASS (§6.1)
```
