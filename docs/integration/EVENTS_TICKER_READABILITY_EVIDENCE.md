# Events ticker readability — PR evidence

## Change summary

| Item | Before (PR #27 / v3) | After (this PR / v4) |
|------|----------------------|----------------------|
| Desktop loop duration | 280s | **840s** (3× slower) |
| Mobile auto-scroll | disabled | **disabled** (unchanged) |
| Pause hover/focus | yes | yes (unchanged) |
| `prefers-reduced-motion` | manual only | manual only (unchanged) |
| Cache bust | `?v=3` | **`?v=4`** |

## Affected files

- `static/js/competitions-ticker.js` — `BASE_DURATION_SEC = 840`
- `templates/index.html` — asset `?v=4`

## Desktop behavior

- RAF scroll moves duplicated track over **840 seconds** per full loop.
- Target: card readable **5–8+ seconds** in typical viewport (Owner visual acceptance required).
- Pause on `mouseenter` / `focusin`; resume after 200–600 ms.

## Mobile behavior (375×812, 390×844)

- `MOBILE_AUTO_SCROLL = false` → `is-manual-only`, no RAF auto tick.
- User scrolls/swipes viewport horizontally only.

## Reduced motion

- `prefers-reduced-motion: reduce` → no clone, no RAF.

## Manual QA checklist (Owner, staging after merge)

- [ ] Desktop: ticker readable; item does not fly by in 1–3 s
- [ ] Desktop: hover/focus pause
- [ ] Mobile 375×812 / 390×844: no auto-scroll; swipe works
- [ ] Hard refresh loads `?v=4`
- [ ] Screenshots desktop + mobile attached

## Automated tests

```bash
python -m pytest tests/unit/test_competitions_ticker.py -q
python -m pytest tests/unit/test_events_public_routes.py::TestTickerLinks -q
```

No JS unit tests for scroll speed (manual QA required).

## Production

Not deployed. `main` unchanged until GM approval.
