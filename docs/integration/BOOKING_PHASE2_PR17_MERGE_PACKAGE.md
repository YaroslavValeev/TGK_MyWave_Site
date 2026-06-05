# BOOKING_PHASE2_PR17 — Final Merge / Release Package

**PR:** #17 — Frontend multi-set UI + boat grid sync `07:00–19:30`
**Branch:** `feature/booking-phase2-pr4-frontend-multiset`
**PR link:** https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/17

| Commit | Hash | Note |
|--------|------|------|
| **Merge commit (`main`)** | `dac582bcfc0212a2074470283b9bb352d163af79` | PR #17 merged |
| **PR HEAD** | `cefd5ca4d90eeb90d7dbdb77960f57c6ac4f89a6` | Whitespace cleanup (docs only) |
| **Functional** | `8f9a07f0bc6045911c6e264e2342b9248edae8af` | PR4 implementation |
| Pre-PR17 `main` | `393ae269` | Docs packages (PR4/staging) |

**CI:** green (`quality-checks` pass)
**Tests:** `81 passed` (booking unit suite)
**TGbotAdmin:** final re-check **PASS** — **MERGE ALLOWED WITH FOLLOW-UP**
**Blockers:** **0**
**GM:** **APPROVED TO MERGE** — merged 2026-06-05

**Policy:** Phase 2 runtime **flags OFF** on prod; flags ON — отдельное approval после staging E2E.

---

## 0. TGbotAdmin review summary

| Round | Result | Blockers |
|-------|--------|----------|
| Initial | CHANGES REQUESTED | trailing whitespace in docs/evidence |
| Re-check | **PASS** — MERGE ALLOWED WITH FOLLOW-UP | **0** |

**Confirmed:** functional code after `8f9a07f0` unchanged; only docs/evidence commits (`b8dc2087`, `cefd5ca4`).

---

## 1. PR #17 merged

**YES** — merged to `main` as `dac582bcfc0212a2074470283b9bb352d163af79`.

---

## 2. Final file list (13 paths vs `393ae269`)

```
app/config/booking_grid.py
app/routes/calendar_routes.py
app/services/booking/availability.py
static/js/booking.js
static/css/style.css
templates/partials/booking_modals.html
tests/unit/test_booking_grid.py
tests/unit/test_boat_slots.py
docs/integration/BOOKING_PHASE2_PR17_REVIEW_PACKAGE.md
docs/integration/evidence/PR17_grid_slots.txt
docs/integration/evidence/PR17_test_output.txt
docs/integration/evidence/PR17_test_output_full.txt
docs/integration/evidence/PR17_ui_reference.html
```

**Out of scope:** prod `.env`, `mywave-node`, `mywave-telegram-bot`, TGbotAdmin code.

---

## 3. Production impact (flags OFF deploy)

| Statement | Status |
|-----------|--------|
| Multi-set UI (`set_count`, picker) | Active only when API returns `max_set_count` (flags ON) |
| POST `set_count` | Only when Phase 2 multi-set path |
| Boat grid displayed slots | **07:00–19:30** even at flags OFF (Owner-approved) |
| Phase 2 pipeline / recheck / 409 | Active only when flags ON |
| All `BOOKING_PHASE2_*` default OFF | YES |

---

## 4. CI / test evidence

**CI (PR #17):** `quality-checks` — pass.

```bash
cd /var/www/mywave
source venv/bin/activate
export SECRET_KEY="${SECRET_KEY:-$(grep -E '^SECRET_KEY=' .env | cut -d= -f2-)}"

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
  -q --tb=short
```

**Expected:** `81 passed`

```bash
grep -E '^BOOKING_PHASE2_' .env || echo "OK: no BOOKING_PHASE2_* in .env"
```

---

## 5. Production deploy commands (flags OFF)

**Execute only in Owner deploy window.**

```bash
sudo MYWAVE_ROOT=/var/www/mywave bash /var/www/mywave/deploy/scripts/backup_mywave.sh

cd /var/www/mywave
git fetch --all --prune
git checkout main
git pull --ff-only origin main

git rev-parse HEAD
# Expected: dac582bcfc0212a2074470283b9bb352d163af79 (or newer doc-only on main)

grep -E '^BOOKING_PHASE2_' .env || echo "OK: no BOOKING_PHASE2_* in .env"

source venv/bin/activate
export SECRET_KEY="${SECRET_KEY:-$(grep -E '^SECRET_KEY=' .env | cut -d= -f2-)}"

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
  -q

sudo systemctl restart mywave-site
```

### Do NOT run

```bash
sudo systemctl restart mywave-node.service
sudo systemctl restart mywave-telegram-bot.service
```

### Do NOT add to `.env` without separate approval

```bash
BOOKING_PHASE2_AVAILABILITY=1
BOOKING_PHASE2_TRAVEL_BUFFER=1
BOOKING_PHASE2_MULTI_SET_BOAT=1
BOOKING_PHASE2_SUMMARY_V2=1
BOOKING_PHASE2_GYM_LOCATION_V2=1
```

---

## 6. Rollback plan

| Scenario | Action |
|----------|--------|
| Pre-PR17 production | `393ae269` (main before PR #17 merge) |
| After deploy | `git checkout 393ae269` (or `git revert dac582bc`) + pull prod + pytest + **restart `mywave-site` only** |
| Runtime | All `BOOKING_PHASE2_*` absent or `0` → Phase 1 POST; grid reverts to pre-PR17 window if code rolled back |

---

## 7. Post-deploy smoke (flags OFF)

Wait **5–10 s** after restart:

```bash
sudo systemctl is-active mywave-site
sudo systemctl status mywave-site --no-pager -l | head -20

curl -fsS https://mywavewake.ru/health
curl -fsS -o /dev/null -w "home %{http_code}\n" https://mywavewake.ru/

# Boat slots grid (legacy path, flags OFF) — first/last start
curl -fsS "https://mywavewake.ru/api/calendar/slots/$(date -u +%Y-%m-%d)?service=boat" \
  -H "Cookie: session=<...>" -H "X-CSRFToken: <...>" | \
  python3 -c "import sys,json; t=[s['time'] for s in json.load(sys.stdin)]; print('first',t[0],'last',t[-1],'count',len(t))"

sudo journalctl -u mywave-site --since "5 min ago" --no-pager | tail -40
```

**Expected:**

- `mywave-site` active
- health/home HTTP 200
- boat slots: first **07:00**, last **19:30**, no 06:00 / 20:00 / 21:00 starts
- booking UI: no multi-set picker (flags OFF), button «Подтвердить запись»

---

## 8. Site confirmations (deploy window)

- [ ] Owner deploy window opened
- [ ] Backup completed
- [ ] `git rev-parse HEAD` = `dac582bc` (or documented newer)
- [ ] pytest **81 passed** on prod host
- [ ] Restart **only** `mywave-site`
- [ ] **Did not** restart `mywave-node.service`
- [ ] **Did not** restart `mywave-telegram-bot.service`
- [ ] Production flags **OFF** / absent in `.env`
- [ ] Post-deploy smoke PASS

---

## 9. Follow-up (before production flags ON)

| Item | Track |
|------|-------|
| Partial Sheets B+E | `feature/booking-phase2-sheets-compensation` — [`BOOKING_PARTIAL_SHEETS_FOLLOWUP.md`](BOOKING_PARTIAL_SHEETS_FOLLOWUP.md) |
| Staging E2E | [`BOOKING_PHASE2_STAGING_E2E_PACKAGE.md`](BOOKING_PHASE2_STAGING_E2E_PACKAGE.md) — **mandatory** before flags ON |
| Prod flags ON | Separate GM approval only |

---

## 10. Related packages

- [`BOOKING_PHASE2_PR17_REVIEW_PACKAGE.md`](BOOKING_PHASE2_PR17_REVIEW_PACKAGE.md)
- [`BOOKING_PHASE2_PR16_MERGE_PACKAGE.md`](BOOKING_PHASE2_PR16_MERGE_PACKAGE.md) — PR #16 prod GREEN baseline
- [`BOOKING_PHASE2_PR4_IMPLEMENTATION_PACKAGE.md`](BOOKING_PHASE2_PR4_IMPLEMENTATION_PACKAGE.md)
