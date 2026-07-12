# Isolated Booking Hotfix #99 — Compare Report

**Date:** 2026-07-13  
**Status:** repository-side ready — **NO merge / NO deploy** without owner GO  
**Production pin (do not leave without GO):** `eab7eb9859054024275df8ae8a5115e1d6830c89`

---

## Release identity

| Item | Value |
|------|-------|
| Branch | `hotfix/booking-add-calendar-from-eab7eb98` |
| Code fix commit | `d9b68b75c81fd256da13fcde5756d17594bb56fa` |
| Branch tip (code + release note) | `1ed5277df4b37633b2cab93a9b7b569fc4d903ae` |
| Base / rollback SHA | `eab7eb9859054024275df8ae8a5115e1d6830c89` |
| Upstream source | PR #99 / `cdb4e59f248518575d1b275d1b0f7508f964d0b9` |
| Method | branch from pin + cherry-pick #99 only |
| Remote | https://github.com/YaroslavValeev/TGK_MyWave_Site/tree/hotfix/booking-add-calendar-from-eab7eb98 |

---

## Compare: `eab7eb98` → branch tip

**Code-only (`d9b68b75`):**
```
static/js/booking.js | 2 ++
 1 file changed, 2 insertions(+)
```

**Branch tip (`1ed5277d`) additionally includes:**
```
docs/deploy/BOOKING_HOTFIX99_ISOLATED_RELEASE.md
```
No Camp / migrations / cron.

### Patch

```diff
+              const venueForCal = getMyWaveVenueFromBody();
+              const calendarLocation = venueForCal.mapUrl || venueForCal.label || '';
               const location = encodeURIComponent(calendarLocation);
```

Fixes `ReferenceError: calendarLocation is not defined` on Google Calendar “add-to-calendar” from booking confirm.

---

## Camp exclusion confirmation

| Check | Result |
|-------|--------|
| Changed files count | **1** (`static/js/booking.js`) |
| Camp API / models / routes | **absent** |
| Camp migrations | **absent** |
| Camp cron / `run_camp_sync.py` | **absent** |
| `CAMP_*` / public flag changes | **absent** |
| `origin/main` / Camp #98 | **not included** |
| Pin is ancestor of release HEAD | **YES** |

`git diff --name-only eab7eb98...HEAD` → only `static/js/booking.js`.

---

## CI / test evidence (local)

Command:

```bash
DISABLE_TELEGRAM=1 ENABLE_GOOGLE_SERVICES=0 python -m pytest \
  tests/unit/test_booking_phase1.py \
  tests/unit/test_booking_confirm_slot_button.py \
  tests/unit/test_booking_config_imports.py \
  tests/unit/test_booking_features.py \
  tests/unit/test_booking_grid.py \
  tests/unit/test_booking_calendar_v2.py \
  tests/unit/test_booking_availability_phase2.py \
  tests/unit/test_hero_booking_season.py \
  tests/unit/test_public_routes_p0.py \
  tests/unit/test_public_button_style.py \
  -q
```

**Result:** `77 passed, 2 warnings` (~40s)

Smoke-compatible static check:

```bash
grep -n "calendarLocation = venueForCal" static/js/booking.js
# expect: present after cherry-pick
```

---

## Explicit non-goals

- No merge to `main`
- No production deploy without owner GO
- No Camp path / `git pull origin main`
- No seasonal booking branch (`feat/booking-seasonal-yclients`) in this release

---

## Production deploy commands (ONLY after owner GO)

```bash
set -euo pipefail
PROD_ROOT=/var/www/mywave
GIT="git -c safe.directory=${PROD_ROOT}"
EXPECTED_HEAD="1ed5277df4b37633b2cab93a9b7b569fc4d903ae"
ROLLBACK_SHA="eab7eb9859054024275df8ae8a5115e1d6830c89"

cd "$PROD_ROOT"

echo "=== PRECHECK ==="
test "$($GIT rev-parse HEAD)" = "$ROLLBACK_SHA" || echo "WARN: prod not exactly on pin (continue only if intentional)"

echo "=== BACKUP ==="
if [ -x deploy/scripts/backup_mywave.sh ]; then
  sudo deploy/scripts/backup_mywave.sh
else
  TS=$(date +%Y%m%d_%H%M%S)
  sudo tar --exclude='./venv' --exclude='./.git' \
    -czf "/root/mywave_before_booking99_${TS}.tar.gz" .
fi

echo "=== DEPLOY ISOLATED BOOKING HOTFIX (NOT main / NOT Camp) ==="
$GIT fetch origin hotfix/booking-add-calendar-from-eab7eb98
$GIT checkout -B deploy/booking-hotfix99 origin/hotfix/booking-add-calendar-from-eab7eb98
test "$($GIT rev-parse HEAD)" = "$EXPECTED_HEAD"

# confirm no Camp — only booking.js (+ release note)
$GIT diff --name-only "$ROLLBACK_SHA"...HEAD
# expect:
#   docs/deploy/BOOKING_HOTFIX99_ISOLATED_RELEASE.md
#   static/js/booking.js

echo "=== RESTART mywave-site ONLY ==="
sudo systemctl restart mywave-site
sleep 12
systemctl is-active mywave-site
curl -fsS https://mywavewake.ru/health/live
curl -fsS -o /dev/null -w "home %{http_code}\n" https://mywavewake.ru/
grep -n "calendarLocation = venueForCal" static/js/booking.js
```

### Rollback

```bash
cd /var/www/mywave
git -c safe.directory=/var/www/mywave checkout eab7eb9859054024275df8ae8a5115e1d6830c89
sudo systemctl restart mywave-site
sleep 12
curl -fsS https://mywavewake.ru/health/live
```

---

## Owner GO checklist

- [ ] Compare report reviewed
- [ ] Camp exclusion confirmed
- [ ] Tests green
- [ ] Explicit GO for production deploy of tip `1ed5277d` (or code-only `d9b68b75`)
- [ ] Deploy executed with EXPECTED_HEAD pin check
- [ ] Manual smoke: booking confirm → “Add to Google Calendar” without JS ReferenceError
