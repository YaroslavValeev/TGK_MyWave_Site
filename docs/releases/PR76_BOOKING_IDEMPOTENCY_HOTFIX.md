# PR76 — Booking idempotency hotfix (production 500)

**PR:** https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/76 (MERGED)  
**Merge commit:** `455c0633`  
**Deployed:** 2026-07-06 MSK  
**Incident:** CLOSED

## Status

| Item | Pre-fix | Post-deploy |
|------|---------|-------------|
| Production HEAD | `3654bbb2` | **`455c0633`** |
| PR75 deploy | partial (UI OK, submit 500) | UI + submit OK |
| PR56 phase-b | PASS | PASS |
| A1 mobile boat booking | FAIL (500) | **PASS (`201`)** |
| Incident `POST /api/calendar/book` | YES | **CLOSED** |
| Rollback | HOLD | **not required** |

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
Squash merge: `fix(booking): PR76 tolerate non-numeric workout duration in idempotency (#76)`

- `_safe_workout_duration_minutes(value)` — try/except around `int(value or 0)`
- `duration_by_id` uses safe helper
- Test: `test_duplicate_skips_non_numeric_workout_duration`

## Pre-merge checks

| Check | Result |
|-------|--------|
| `pytest tests/unit/test_booking_phase1.py::TestIdempotency` | PASS |
| `pytest tests/unit/test_booking_confirm_slot_button.py` (PR75) | PASS |
| `pytest tests/unit/test_booking_phase1.py` + `test_booking_pipeline_phase2.py` (28 tests) | PASS |
| CI `quality-checks` on PR #76 | PASS |

## Deploy scope

- Python backend hotfix only
- No `.env`, DB migrations, Sheets schema, TGbotAdmin/node, Notifications v2
- `sudo systemctl restart mywave-site`

```bash
cd /var/www/mywave
git fetch origin
git pull origin main
git log -1 --oneline   # expect 455c0633
sudo systemctl restart mywave-site
sleep 6
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5000/health/live
```

## Post-deploy smoke (2026-07-06)

| Check | Result |
|-------|--------|
| `git log -1` | `455c0633` |
| health/live | 200 |
| slots boat `2026-07-09` | 200 |
| PR56 phase-b | PASS |
| A1 mobile boat confirm | **PASS** |

```bash
bash automation/production/prod_pr56_smoke.sh --phase-b
```

## Post-deploy evidence (A1)

### Nginx access — `POST /api/calendar/book`

| Time (MSK) | HTTP | Note |
|------------|------|------|
| 07:13:59 | 500 | pre-PR76 |
| 07:14:11 | 500 | pre-PR76 |
| 07:20:19 | 500 | pre-PR76 |
| **08:09:24** | **201** | **post-PR76 — success** |

```bash
grep "POST /api/calendar/book" /var/log/nginx/access.log | tail -5
```

### App log (same successful request ~08:09)

```
booking_calendar_event_created
booking_row_written
booking_row_written
booking_pipeline_ok workout_id_tail=jomejkto client_id_tail=44886029
```

```bash
tail -50 /var/www/mywave/logs/app.log | grep -iE "book|бронир|calendar"
```

### Mobile QA (Owner)

- Modal: **«Успешно забронировано»**
- Date: 2026-07-07, time: 10:00, service: Катер, 2 сета (10:00, 10:30)
- No `ValueError ... 'Зал'` in logs after deploy

## Follow-up (non-blocking)

| Item | Priority |
|------|----------|
| **Add to calendar** on Android — toast «Не удалось добавить событие…» | separate ticket (`.ics` / Web Share) |
| **Data hygiene** — Google Sheets `Workouts`: `duration` = numeric minutes | ops / sheets cleanup |
| A2 / I1 / T1 per release handoff | next QA items |

## Data hygiene (Sheets)

Review `Workouts` tab: `duration` must be numeric minutes; location (e.g. `Зал`) must not sit in `duration`. PR76 protects production from bad rows but does not fix source data.
