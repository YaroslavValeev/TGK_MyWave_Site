# PR76 — Booking idempotency hotfix (production 500)

## Status

| Item | Value |
|------|-------|
| Production HEAD (pre-fix) | `3654bbb2` |
| PR75 deploy | partial (UI OK, submit 500) |
| PR56 phase-b | PASS |
| A1 mobile boat booking | FAIL on final confirm (500) |
| Incident | YES — `POST /api/calendar/book` |
| Rollback | HOLD / not recommended |

## Root cause

```
POST /api/calendar/book → 500
app/services/booking/idempotency.py → is_duplicate_web_booking()
duration_by_id dict comprehension
ValueError: invalid literal for int() with base 10: 'Зал'
```

`Workouts.duration` may contain non-numeric text (shifted column / manual entry). Direct `int(w.get("duration") or 0)` crashed the pipeline before idempotency completed.

## Fix

Branch: `hotfix/booking-idempotency-safe-duration`  
Commit: `fix(booking): tolerate non-numeric workout duration in idempotency`

- `_safe_workout_duration_minutes(value)` — try/except around `int(value or 0)`
- `duration_by_id` uses safe helper
- Test: `test_duplicate_skips_non_numeric_workout_duration`

## Pre-merge checks

```bash
pytest tests/unit/test_booking_phase1.py::TestIdempotency -q
pytest tests/unit/test_booking_confirm_slot_button.py -q
pytest tests/unit/test_booking_phase1.py tests/unit/test_booking_pipeline_phase2.py -q
```

## Deploy scope (Owner, after merge only)

- Python backend hotfix only
- No `.env`, DB migrations, Sheets schema, TGbotAdmin/node, Notifications v2
- `sudo systemctl restart mywave-site`

```bash
cd /var/www/mywave
git fetch origin
git pull origin main
sudo systemctl status mywave-site --no-pager
sudo systemctl restart mywave-site
sudo systemctl status mywave-site --no-pager
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5000/health/live
```

**Do not deploy before merge** — `git pull origin main` stays at `3654bbb2` until PR76 is merged.

## Post-deploy smoke

```bash
bash automation/production/prod_pr56_smoke.sh --phase-b
curl -sS -o /dev/null -w '%{http_code}\n' "http://127.0.0.1:5000/api/calendar/slots/2026-07-09?service=boat"
curl -sS https://mywavewake.ru/ | grep -o 'booking-mobile.css?v=booking-slot-btn1'
journalctl -u mywave-site --since "5 min ago" --no-pager | grep -iE "booking|ERROR|Traceback" | tail -30
```

| Check | Expected |
|-------|----------|
| health/live | 200 |
| health/ready | 200 |
| PR56 phase-b | PASS |
| booking-mobile.css cache buster | present |
| A1 mobile boat confirm | PASS (200/409, not 500) |

## Data hygiene (follow-up, non-blocking)

Review Google Sheets `Workouts`: `duration` = numeric minutes; location must not sit in `duration`.
