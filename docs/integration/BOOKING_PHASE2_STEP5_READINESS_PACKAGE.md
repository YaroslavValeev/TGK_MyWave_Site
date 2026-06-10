# BOOKING Phase 2 — Step 5 Readiness Package

**From:** Site MyWave  
**To:** GM / TGbotAdmin  
**Date:** 2026-06-11  
**Status:** **READINESS ONLY — Step 5 NOT APPROVED / HOLD**  
**Prod HEAD (current):** `7cc11265`  
**Step 4:** **PASS** (GM formal + TGbotAdmin NO-ALERT WITH NOTES)

---

## 0. Executive summary

| Item | Value |
|------|--------|
| **Step 5 flag candidate** | `BOOKING_PHASE2_GYM_LOCATION_V2=1` |
| **Venue constants on prod** | **NO** — prod still at `7cc11265` without canonical map URLs |
| **Venue constants in repo** | **YES** — local working tree (uncommitted); see §2 |
| **Tests (local)** | **9 passed** (venue canonical + location v2 writer flags) |
| **Prerequisite before Step 5 flag** | Code-only deploy of venue constants → prod HEAD > `7cc11265` |
| **Step 5 execution** | Await GM `Step 5 APPROVED` |

---

## 1. Current production flags (unchanged)

```text
BOOKING_PHASE2_AVAILABILITY=1
BOOKING_PHASE2_TRAVEL_BUFFER=1
BOOKING_PHASE2_MULTI_SET_BOAT=1
BOOKING_PHASE2_SUMMARY_V2=1
BOOKING_PHASE2_GYM_LOCATION_V2=0
```

---

## 2. A. Venue constants evidence

### GM canonical URLs

| Venue | URL |
|-------|-----|
| Gym / Зал / DoAflip | `https://yandex.ru/maps/-/CPh6b6jY` |
| Boat / MyWave Wake | `https://yandex.ru/maps/org/mywave_wake/90003306477?si=1zaxyu7g67ct9pe6658pvtewag` |

### Files changed (repo working tree)

| File | Constant / field | Change |
|------|------------------|--------|
| `app/config/booking_venues.py` | `GYM_VENUE["yandex_maps_url"]` | `CLWQy6-I` → `CPh6b6jY` |
| `app/config/venue.py` | `MYWAVE_VENUE["yandex_maps_url"]` | add `?si=1zaxyu7g67ct9pe6658pvtewag` |
| `app/services/booking/constants.py` | `BOAT_CALENDAR_LOCATION` | canonical boat URL with `?si=...` |
| `tests/unit/test_venue_canonical_maps.py` | `GM_GYM_MAP`, `GM_BOAT_MAP` | **new** regression tests |

Related (Step 4 tooling, optional in same commit):

| File | Purpose |
|------|---------|
| `automation/production/prod_step4_verify_readonly.sh` | read-only Step 4 verify |

### Commit / branch / PR

| Item | Status |
|------|--------|
| **Commit hash** | **PENDING** — changes not yet committed on `main` |
| **Branch** | `main` (local) |
| **PR** | **PENDING** — commit + push required before code-only deploy |
| **On production (`7cc11265`)** | **NO** |

### Local test command and result

```bash
python -m pytest tests/unit/test_venue_canonical_maps.py \
  tests/unit/test_booking_calendar_v2.py::TestWriterFlags -q
```

**Result:** `9 passed`

Minimal GM-requested subset (`test_venue_canonical_maps` + summary v2): **7 passed** (3 venue + 4 summary from prior run).

---

## 3. Step 5 writer / location contract (when flag ON)

`BOOKING_PHASE2_GYM_LOCATION_V2=1` affects **Calendar `location` field** for **new Site web events** via `get_calendar_location()`:

| `service_type` | Location v1 (current prod) | Location v2 (Step 5) |
|----------------|---------------------------|----------------------|
| `gym` | `Зал MyWave` | `Зал` |
| `boat` | `MyWave Wake — https://yandex.ru/maps/...` | `Катер` |

**UX / confirmation maps** (not Calendar location when v2 ON):

- Gym: `BOOKING_VENUES["gym"]["yandex_maps_url"]` → DoAflip canonical
- Boat: `MYWAVE_VENUE["yandex_maps_url"]` / `BOAT_CALENDAR_LOCATION` → MyWave Wake canonical

**Unchanged:**

- Web summary: `(WEB_ID: bk_...)` (Step 4)
- Telegram path: `(ID: tg_id)` v1 summary
- TGbotAdmin-created events: not modified by Site flags

---

## 4. B. Production readiness — code-only deploy (required before Step 5 flag)

Venue constants are **not** on prod. Sequence:

### Phase A — code-only deploy (flags unchanged)

1. Commit + push venue constants (+ tests) to `origin/main`
2. On prod: `git fetch` + `git checkout`/`reset` to new HEAD
3. **Do not** change `BOOKING_PHASE2_*` in `.env`
4. Restart **`mywave-site` only** (loads new Python constants)
5. Read-only verify: grep canonical URLs in prod files; flags unchanged

### Phase B — Step 5 flag (only after GM `Step 5 APPROVED`)

1. Snapshot `.env`
2. Set `BOOKING_PHASE2_GYM_LOCATION_V2=1` only
3. Restart `mywave-site` only
4. Smoke + location dry-run (§6)

---

## 5. Read-only prod verification (prove venue NOT on prod yet)

Run on prod **before** code-only deploy:

```bash
cd /var/www/mywave
git -c safe.directory=/var/www/mywave rev-parse --short HEAD
grep -n 'yandex_maps_url\|BOAT_CALENDAR_LOCATION' \
  app/config/booking_venues.py app/config/venue.py app/services/booking/constants.py
```

**Expected at `7cc11265`:** gym URL contains `CLWQy6-I`; boat URL **without** `?si=1zaxyu7g67ct9pe6658pvtewag`.

After code-only deploy, same grep must show `CPh6b6jY` and `?si=...`.

---

## 6. C. Step 5 smoke plan (after GM approval)

### Pre-smoke (flags after Step 5 enable)

```text
BOOKING_PHASE2_AVAILABILITY=1
BOOKING_PHASE2_TRAVEL_BUFFER=1
BOOKING_PHASE2_MULTI_SET_BOAT=1
BOOKING_PHASE2_SUMMARY_V2=1
BOOKING_PHASE2_GYM_LOCATION_V2=1
```

### Checks

| # | Check | PASS criteria |
|---|--------|---------------|
| 1 | `/health` | HTTP 200; database OK; google OK |
| 2 | Public routes | `/` 200; `/blog` 200; `/booking` 308 |
| 3 | Boat slots | Response OK; `max_set_count` on available rows |
| 4 | Gym slots | Response OK; `remaining` present |
| 5 | Location dry-run | gym → `Зал`; boat → `Катер`; WEB_ID marker on web; `(ID:)` on TG path |
| 6 | Logs | No booking writer ERROR / Traceback |
| 7 | Guardrails | No test bookings; Node/TG bot not restarted |

### Location dry-run (no Calendar insert)

Simulate `GYM_LOCATION_V2=1` in process env or after flag enable:

```python
from app.services.booking.calendar_writer import get_calendar_location, resolve_event_summary, build_event_summary
# gym location v2: "Зал"
# boat location v2: "Катер"
# web summary still WEB_ID; telegram still (ID:)
```

---

## 7. Rollback

### Rollback Step 5 flag only

Restore snapshot `.env.step5_gym_location_v2_<TS>` or set `GYM_LOCATION_V2=0`; restart `mywave-site`. Steps 1–4 flags remain ON.

### Rollback code-only deploy

`git checkout 7cc11265` (or restore known-good HEAD) + restart `mywave-site`; flags unchanged.

---

## 8. Guardrails (until Step 5 APPROVED)

- Do not enable `BOOKING_PHASE2_GYM_LOCATION_V2=1`
- Do not bundle Steps 4+5 retroactively without approval
- Do not `.env` dedupe
- Do not create prod test bookings
- Do not restart `mywave-node` / `mywave-telegram-bot`
- Do not touch `/opt/mywave-bot`
- Do not change Calendar/Sheet IDs

---

## 9. Site backlog (non-blocking)

- `blog_post` table missing
- `parser_news_sheet` / blog-store Sheets read error
- socket / invalid session logs

---

## 10. Next action

1. **Site:** commit + push venue constants → provide commit hash to GM
2. **GM:** approve code-only deploy (flags OFF)
3. **Site:** code-only deploy to prod → read-only URL proof
4. **GM:** `Step 5 APPROVED` or HOLD
5. **Site:** Step 5 enable block + smoke
6. **TGbotAdmin:** post-Step-5 monitoring
