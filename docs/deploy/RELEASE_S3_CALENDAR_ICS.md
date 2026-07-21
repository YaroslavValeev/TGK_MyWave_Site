# Release S3 — Client Calendar / ICS UX

**Branch:** `release/s3-calendar-ics-ux`  
**Base:** production tip after S3a (`b37c8651` / deploy pin)  
**Scope:** client-facing Google Calendar + `.ics` only (trainer SoT `calendar_writer` **unchanged**)

## What changed

| Area | Change |
|---|---|
| SUMMARY | `Катер MyWave — {имя}` / `Зал MyWave — {имя}` (no `boat`/`gym` tokens) |
| LOCATION | Canonical venue label (boat = MyWave Wake start label; gym = `Зал MyWave`) |
| Map URL | In DESCRIPTION / details, not in LOCATION |
| Duration | boat = N×30 min; gym = 90 min |
| Venues inject | `data-mw-booking-venues` + legacy `data-mw-*` from Flask context |
| Cache bust | `booking.js?v=s3-calendar-ics-ux` |

## Files

- `app/services/booking/client_calendar.py` — title / duration / ICS / GCal helpers
- `app/__init__.py` — context processor
- `templates/base.html` — venue attrs + cache bust
- `static/js/booking.js` — success modal ICS/GCal
- `tests/unit/test_client_calendar.py`

## Verify locally

```bash
python -m pytest tests/unit/test_client_calendar.py -q
```

## Deploy (Owner) — after GO

See sequential server blocks in chat / SITE_COMPLETION_PLAN.  
Restart **only** `mywave-site.service`.  
Do **not** touch `mywave-node`, `mywave-telegram-bot`.

## Rollback

`git checkout <pre-S3-SHA> -- .` then restart site, or flip branch to previous pin.
