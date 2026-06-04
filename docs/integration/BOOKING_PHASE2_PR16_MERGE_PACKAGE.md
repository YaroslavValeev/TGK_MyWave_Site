# BOOKING_PHASE2_PR16 — Final Merge / Release Package

**PR:** #16 — Pipeline recheck + writer v2 + idempotency range + 409
**Branch:** `feature/booking-phase2-pr3-pipeline-writer`
**PR link:** https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/16

| Commit | Hash | Note |
|--------|------|------|
| **PR HEAD** | `a4ae771d5d14b7f29da40f691359446b1f184423` | Merge package final (docs) |
| **Runtime (review)** | `9004d3bbdb9858bb9ba43e59541da4a0d42fc76a` | TGbotAdmin blocker fixes |
| Initial | `116af0d563574ae78267b637c453dcadfb724e2b` | PR3 implementation |

**CI:** green (`quality-checks` pass)
**Tests:** `75 passed` (prod deploy)
**TGbotAdmin:** round 2 **PASS** — **MERGE ALLOWED WITH FOLLOW-UP**
**Blockers:** **0**
**Merge commit (`main`):** `cf318cdcc2b0ca4566ec9dd4801801c843ecf2b9`
**Production deploy:** **GREEN** (flags OFF, 2026-06-04)

**Policy:** Phase 2 runtime **flags OFF** on prod; flags ON — отдельное approval.

---

## 0. TGbotAdmin review

| Round | Result | Blockers | Commit |
|-------|--------|----------|--------|
| 1 | CHANGES REQUESTED | 2 | `116af0d5` |
| 2 | **PASS** — MERGE ALLOWED WITH FOLLOW-UP | **0** | `9004d3bb` |

### Blockers closed (round 2)

| # | Item | Status |
|---|------|--------|
| 1 | Boat location v2: `get_calendar_location("boat")` and event body `location: Катер` when `BOOKING_PHASE2_GYM_LOCATION_V2=1` | Closed |
| 2 | Calendar read `day ± TRAINER_TRAVEL_BUFFER_MINUTES`; cross-day buffer tests | Closed |

**Flags OFF:** boat location remains Phase 1 `MyWave Wake — ...`.

---

## 0.1 Non-blocker risks (2 accepted — follow-up)

### Risk 1 — Boat slot grid mismatch (follow-up before staging E2E)

| System | Boat grid |
|--------|-----------|
| Site | 06:00–21:00 |
| TGbotAdmin | 07:00–19:30 |

**Owner decision required before staging E2E:** sync grids OR accept divergence and document edge cases (06:00–07:00, 19:30–21:00).

**PR #16:** grid unchanged.

### Risk 2 — Partial Sheets failure (follow-up before production flags ON)

**Scenario:** `write_workout_row()` OK + `write_client_workout_row()` fail → possible orphan `Workouts` row.

**Position for PR #16:** **accepted risk for merge**; transaction / compensation / repair job — **follow-up before production flags ON**.

**Mitigation (ops):** manual cleanup of orphan `Workouts` by `workout_id` without `Client_Workouts` pair if incident occurs.

---

## 1. Final file list (15 paths vs `main`)

```
app/config/booking_venues.py
app/modules/sheets.py
app/routes/calendar_routes.py
app/schemas/__init__.py
app/services/booking/__init__.py
app/services/booking/availability.py
app/services/booking/calendar_reader.py
app/services/booking/calendar_writer.py
app/services/booking/idempotency.py
app/services/booking/pipeline.py
app/services/booking/sheets_writer.py
tests/unit/test_booking_calendar_v2.py
tests/unit/test_booking_pipeline_phase2.py
tests/unit/test_booking_calendar_reader_buffer.py
tests/unit/test_booking_features.py
docs/integration/BOOKING_PHASE2_PR16_MERGE_PACKAGE.md
```

**Out of scope:** `static/js/booking.js` (PR4), prod `.env`, `mywave-node`, `mywave-telegram-bot`, TGbotAdmin code.

---

## 2. Production impact (flags OFF deploy)

| Statement | Status |
|-----------|--------|
| POST pipeline at flags OFF | Phase 1 unchanged |
| Writer v2 / 409 / buffer / range idempotency | Active only when flags ON |
| All `BOOKING_PHASE2_*` default OFF | YES |
| Phase 2 booking complete | NO (PR4 + staging E2E + flags approval) |

---

## 3. CI / test evidence

**CI (PR #16):** `quality-checks` — pass.

```bash
cd /var/www/mywave
source venv/bin/activate
export SECRET_KEY="${SECRET_KEY:-$(grep -E '^SECRET_KEY=' .env | cut -d= -f2-)}"

python -m pytest tests/unit/test_booking_availability_phase2.py \
  tests/unit/test_booking_features.py \
  tests/unit/test_booking_phase1.py \
  tests/unit/test_boat_slots.py \
  tests/unit/test_booking_calendar_v2.py \
  tests/unit/test_booking_pipeline_phase2.py \
  tests/unit/test_booking_calendar_reader_buffer.py -q
```

**Expected:** `75 passed`

```bash
grep -E '^BOOKING_PHASE2_' .env || echo "OK: no BOOKING_PHASE2_* in .env"
```

---

## 4. Production deploy commands (flags OFF)

**Execute only after Owner final merge approval.**

```bash
sudo MYWAVE_ROOT=/var/www/mywave bash /var/www/mywave/deploy/scripts/backup_mywave.sh

cd /var/www/mywave
git fetch --all --prune
git checkout main
git pull --ff-only origin main

git rev-parse HEAD

grep -E '^BOOKING_PHASE2_' .env || echo "OK: no BOOKING_PHASE2_* in .env"

source venv/bin/activate
export SECRET_KEY="${SECRET_KEY:-$(grep -E '^SECRET_KEY=' .env | cut -d= -f2-)}"

python -m pytest tests/unit/test_booking_availability_phase2.py \
  tests/unit/test_booking_features.py \
  tests/unit/test_booking_phase1.py \
  tests/unit/test_boat_slots.py \
  tests/unit/test_booking_calendar_v2.py \
  tests/unit/test_booking_pipeline_phase2.py \
  tests/unit/test_booking_calendar_reader_buffer.py -q

sudo systemctl restart mywave-site
```

**Do NOT run:**

```bash
sudo systemctl restart mywave-node.service
sudo systemctl restart mywave-telegram-bot.service
```

**Do NOT add to `.env` without separate approval:**

```bash
BOOKING_PHASE2_AVAILABILITY=1
BOOKING_PHASE2_TRAVEL_BUFFER=1
BOOKING_PHASE2_MULTI_SET_BOAT=1
BOOKING_PHASE2_SUMMARY_V2=1
BOOKING_PHASE2_GYM_LOCATION_V2=1
```

---

## 5. Rollback plan

| Scenario | Action |
|----------|--------|
| Pre-PR16 production | `4584cc87c0593ec67dd3dae8a069eadd62eac01c` (PR #15) |
| After deploy | `git revert <merge-commit>` on `main` + pull prod + pytest + **restart `mywave-site` only** |
| Runtime | All `BOOKING_PHASE2_*` absent or `0` → Phase 1 behavior |

---

## 6. Post-deploy smoke (flags OFF)

Wait **5–10 s** after restart, then:

```bash
sudo systemctl is-active mywave-site
sudo systemctl status mywave-site --no-pager -l | head -20

curl -fsS https://mywavewake.ru/health
curl -fsS -o /dev/null -w "robots %{http_code}\n" https://mywavewake.ru/robots.txt
curl -fsS -o /dev/null -w "home %{http_code}\n" https://mywavewake.ru/

sudo journalctl -u mywave-site --since "5 min ago" --no-pager | tail -40
```

**Expected:** `active`, health/home `200`, Phase 1 booking unchanged.

---

## 7. Post-deploy roadmap

1. ~~Merge PR #16~~ **DONE** (`cf318cdc`)
2. ~~Deploy flags OFF~~ **GREEN**
3. **Next:** staging E2E planning + Owner grid decision (Risk 1)
4. **Next:** PR4 frontend (`set_count` UI)
5. Phased prod flags ON — **отдельное approval** (Risk 2 follow-up recommended first)

---

## 8. Site confirmations

- [x] TGbotAdmin round 2: **PASS** — MERGE ALLOWED WITH FOLLOW-UP
- [x] Blockers: **0**
- [x] Non-blocker risks: **2 accepted** (§0.1)
- [x] Owner final merge approval
- [x] Merge PR #16
- [x] Production deploy flags OFF — **GREEN**
- [x] Restart **only** `mywave-site`
- [x] **Did not** restart `mywave-node.service`
- [x] **Did not** restart `mywave-telegram-bot.service`
- [x] Production flags **OFF** / absent in `.env`

---

## 9. Production deploy record (flags OFF) — GREEN

**Date:** 2026-06-04
**Host:** `mywavewake.ru` / `/var/www/mywave`
**Git HEAD (expected):** `cf318cdcc2b0ca4566ec9dd4801801c843ecf2b9`

| Check | Result |
|-------|--------|
| `mywave-site` | active/running |
| pytest (booking suite) | **75 passed** |
| `/health` | HTTP 200 (`degraded` — optional services only) |
| `/` | 200 |
| `/robots.txt` | 200 |
| `/privacy` | 200 |
| `/offer` | 200 |
| Fatal log scan after restart | PASS |
| `mywave-telegram-bot.service` | active, **not restarted** |
| `mywave-node.service` | active, **not restarted** |
| `BOOKING_PHASE2_*` in prod `.env` | OFF / absent |

**Runtime booking (flags OFF):** Phase 1 POST/pipeline unchanged; PR3 recheck/writer v2/409 active only when flags ON.

### Follow-up (before staging E2E / prod flags ON)

1. **Boat grid mismatch** — Owner decision: Site 06:00–21:00 vs TGbotAdmin 07:00–19:30
2. **Partial Sheets / orphan Workouts** — transaction, compensation, repair job, documented cleanup procedure
