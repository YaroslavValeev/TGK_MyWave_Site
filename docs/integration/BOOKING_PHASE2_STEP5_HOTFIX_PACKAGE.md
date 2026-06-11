# BOOKING Phase 2 — Step 5 Circular-Import Hotfix Package

**From:** Site MyWave  
**To:** GM / TGbotAdmin  
**Date:** 2026-06-12  
**Status:** **HOTFIX READY — await GM code-only deploy approval**  
**Prod state:** Step 4 PASS, Step 5 ROLLED BACK (`GYM_LOCATION_V2=0`, HEAD `7cc11265`)

---

## 0. Root cause

Step 5 failed with:

```text
ImportError: cannot import name 'BOOKING_VENUES' from partially initialized module 'app.config.booking_venues'
```

Import cycle:

```text
app.config.booking_venues
  -> app.services.booking.constants
  -> app.services.booking.__init__
  -> app.services.booking.pipeline
  -> app.services.booking.calendar_writer
  -> app.config.booking_venues
```

**Classification:** Site Step 5 circular-import blocker (not TGbotAdmin regression).

---

## 1. Fix

New neutral config module (no service imports):

```text
app/config/booking_location_constants.py
```

Constants:

| Name | Value |
|------|--------|
| `GYM_CALENDAR_LOCATION` | `Зал` (v2 label) |
| `BOAT_CALENDAR_LOCATION` | `Катер` (v2 label) |
| `BOAT_CALENDAR_LOCATION_V1` | full MyWave Wake URL string (Phase 1) |

**Rule enforced:** `app/config/*` does **not** import from `app/services/booking/*`.

### Files changed

| File | Change |
|------|--------|
| `app/config/booking_location_constants.py` | **new** neutral constants |
| `app/config/booking_venues.py` | import from `booking_location_constants` only |
| `app/services/booking/constants.py` | re-export `BOAT_CALENDAR_LOCATION` from V1 URL |
| `app/services/booking/calendar_writer.py` | use neutral constants; remove `BOOKING_VENUES` import |
| `tests/unit/test_booking_config_imports.py` | **new** import-cycle regression tests |

Venue map URLs (`CPh6b6jY`, boat `?si=...`) unchanged from commit `18938153`.

---

## 2. Test evidence

```bash
python -m pytest \
  tests/unit/test_venue_canonical_maps.py \
  tests/unit/test_booking_calendar_v2.py \
  tests/unit/test_booking_features.py \
  tests/unit/test_booking_config_imports.py \
  -q
```

**Result:** `30 passed`

Import check:

```bash
python -c "
from app.config.booking_venues import BOOKING_VENUES
from app.services.booking.calendar_writer import get_calendar_location
print('IMPORT_OK')
"
```

**Expected:** `IMPORT_OK`

Config guard:

```bash
grep -R "app.services.booking" app/config || true
```

**Expected:** no matches

---

## 3. Production readiness

| Item | Status |
|------|--------|
| Prod HEAD | `7cc11265` (Step 5 rolled back) |
| Prod flags | Steps 1–4 ON, `GYM_LOCATION_V2=0` |
| Hotfix on prod | **NO** — pending commit deploy |

### Sequence (GM-approved order)

1. **Code-only deploy hotfix** (flags unchanged, `GYM_LOCATION_V2=0`)
2. Import check on prod (`IMPORT_OK`)
3. GM separate **Step 5 retry APPROVED**
4. Enable `GYM_LOCATION_V2=1` only + smoke

---

## 4. Code-only deploy commands (flags unchanged)

```bash
set -euo pipefail
export PROD_ROOT=/var/www/mywave
export TARGET_COMMIT=<HOTFIX_COMMIT_HASH>
cd "$PROD_ROOT"
TS=$(date +%Y%m%d_%H%M%S)

cp -a .env "/var/backups/mywave/.env.before_step5_hotfix_${TS}"

git -c safe.directory="$PROD_ROOT" fetch origin main
git -c safe.directory="$PROD_ROOT" checkout "$TARGET_COMMIT"

grep -E '^BOOKING_PHASE2_' .env   # must still show GYM_LOCATION_V2=0

./venv/bin/python -c "
from app.config.booking_venues import BOOKING_VENUES
from app.services.booking.calendar_writer import get_calendar_location
print('IMPORT_OK')
"

systemctl restart mywave-site && sleep 10
systemctl is-active mywave-site
curl -fsS https://mywavewake.ru/health
```

---

## 5. Step 5 retry (NOT approved yet)

Only after hotfix deploy + GM `Step 5 retry APPROVED`:

- enable `BOOKING_PHASE2_GYM_LOCATION_V2=1` only
- restart `mywave-site` only
- dry-run: `gym_loc=Зал`, `boat_loc=Катер`, `step5_dry_run: PASS`

---

## 6. Guardrails

- No bundle rollout
- No `.env` dedupe
- No prod test bookings without approval
- No Node / Telegram bot restart
- No `/opt/mywave-bot` changes
- P1 TGbotAdmin hotfix remains separate
