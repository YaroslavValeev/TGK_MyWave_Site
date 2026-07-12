# Isolated Booking Hotfix #99 — Compare Report

**Status:** repository-side release path ready. **No merge / no deploy without owner GO.**

**Production pin (keep):** `eab7eb9859054024275df8ae8a5115e1d6830c89`  
**Isolated branch:** `hotfix/booking-add-calendar-from-eab7eb98`  
**Release commit:** `d9b68b75c81fd256da13fcde5756d17594bb56fa`  
**Rollback SHA:** `eab7eb9859054024275df8ae8a5115e1d6830c89`  
**Upstream source:** `cdb4e59f` (`#99` on `main`) — cherry-picked only

---

## Scope

| Item | Value |
|------|-------|
| Goal | Fix `calendarLocation` ReferenceError on add-to-calendar |
| Base | production pin `eab7eb98` |
| Changed files | **1** — `static/js/booking.js` |
| Camp API / models / migrations / cron / sync / public flag | **absent** |

### Diff `eab7eb98...d9b68b75`

```diff
+ const venueForCal = getMyWaveVenueFromBody();
+ const calendarLocation = venueForCal.mapUrl || venueForCal.label || '';
```

---

## Anti-Camp confirmation

```text
git diff --name-only eab7eb98...d9b68b75
→ static/js/booking.js   (ONLY)

No matches for: camp, CAMP_, migrations/, run_camp_sync, camp_models
pin is ancestor of release commit: YES
```

---

## Tests (local evidence)

Run on branch `hotfix/booking-add-calendar-from-eab7eb98`:

```bash
DISABLE_TELEGRAM=1 ENABLE_GOOGLE_SERVICES=0 \
  python -m pytest \
  tests/unit/test_booking_phase1.py \
  tests/unit/test_booking_confirm_slot_button.py \
  tests/unit/test_booking_config_imports.py \
  tests/unit/test_booking_features.py \
  tests/unit/test_booking_grid.py \
  tests/unit/test_hero_booking_season.py \
  tests/unit/test_public_routes_p0.py \
  tests/unit/test_public_button_style.py \
  -q
```

CI: push branch → GitHub Actions on PR (create PR against `main` or document as deploy-only branch). **Merge to `main` optional;** production may deploy branch tip directly from pin.

---

## NOT included (explicit)

- Camp PR #98 / Tour contract
- `origin/main` tip (`cdb4e59f` includes Camp ancestry)
- Seasonal booking / hero YCLIENTS branch (`feat/booking-seasonal-yclients`)
- Camp env / `CAMP_PUBLIC_ENABLED` / `run_camp_sync.py`

---

## Tour Camp probe (separate track — STOP for Site Camp)

```bash
# Replace YOUR_TOKEN with MYWAVE_TOUR_CAMP_API_TOKEN (private)
curl -sS -o /tmp/tour_camps_probe.json -w "HTTP %{http_code}\n" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  "https://api.mywavetour.ru/api/v1/camps?status=published&sports=wakesurf,wakeboard&audience=ru&limit=1&offset=0"
head -c 300 /tmp/tour_camps_probe.json; echo
```

Expected while STOP: HTML/`Cannot GET` / 404. Site Camp deploy remains blocked until 200 + `{items,next_offset}`.

---

## Production commands (owner GO only)

```bash
set -euo pipefail
PROD_ROOT=/var/www/mywave
GIT="git -c safe.directory=${PROD_ROOT}"
EXPECTED_HEAD="d9b68b75c81fd256da13fcde5756d17594bb56fa"
ROLLBACK_SHA="eab7eb9859054024275df8ae8a5115e1d6830c89"

cd "$PROD_ROOT"

# Precheck — stay off origin/main Camp tip
echo "current=$($GIT rev-parse HEAD)"
systemctl is-active mywave-site

# Backup
if [ -x deploy/scripts/backup_mywave.sh ]; then
  sudo deploy/scripts/backup_mywave.sh
else
  TS=$(date +%Y%m%d_%H%M%S)
  sudo tar --exclude='./venv' --exclude='./.git' \
    -czf "/root/mywave_before_booking99_${TS}.tar.gz" .
fi

# Fetch isolated branch, then pin to CODE-ONLY commit (not docs tip)
$GIT fetch origin hotfix/booking-add-calendar-from-eab7eb98
$GIT checkout -B deploy/booking-hotfix-99 "$EXPECTED_HEAD"
test "$($GIT rev-parse HEAD)" = "$EXPECTED_HEAD"

# Anti-Camp file check
$GIT diff --name-only "$ROLLBACK_SHA"...HEAD
# expect ONLY: static/js/booking.js

# No Camp env, no migration, no sync
# Restart site only
sudo systemctl restart mywave-site
sleep 15
curl -sf https://mywavewake.ru/health/live && echo HEALTH_OK
systemctl is-active mywave-site

# Smoke
grep -n "calendarLocation = venueForCal" static/js/booking.js
curl -s https://mywavewake.ru/ | grep -q 'booking.js' && echo BOOKING_JS_OK
```

### Rollback

```bash
cd /var/www/mywave
git -c safe.directory=/var/www/mywave checkout eab7eb9859054024275df8ae8a5115e1d6830c89
sudo systemctl restart mywave-site
sleep 12
curl -sf https://mywavewake.ru/health/live
```
