# PR53.2 — competitions mobile autoplay + Telegram status cleanup

## Root cause (carousel)
`static/js/competitions-ticker.js` had `MOBILE_AUTO_SCROLL = false` — mobile was manual-only by design.

## Fix
- `MOBILE_AUTO_SCROLL = true` — same `BASE_DURATION_SEC = 840` as desktop
- Touch pause/resume unchanged (`scheduleResume` after swipe)

## Telegram status
- `shop.py`: notify payload uses literal `status: new`
- `application_notifications._normalize_lead_status()` blocks Mock/object repr

## Tests
```bash
pytest tests/unit/test_pr532_carousel_notify.py tests/unit/test_application_notifications.py tests/unit/test_competitions_ticker.py -q
```

Deploy status: **NOT STARTED**
