# Events ticker readability — PR evidence

## Change summary

| Item | Before (`edca399f`) | After (this PR) |
|------|---------------------|-----------------|
| Desktop loop duration | 135s | **280s** |
| Mobile auto-scroll | 105s RAF | **disabled** (manual swipe only) |
| Pause hover/focus | yes | yes (unchanged) |
| `prefers-reduced-motion` | manual only | manual only (unchanged) |
| Cache bust | `?v=2` | **`?v=3`** |

## Affected files

- `static/js/competitions-ticker.js` — `BASE_DURATION_SEC`, `MOBILE_AUTO_SCROLL`, `shouldAutoScroll()`
- `templates/index.html` — asset `?v=3`

## Desktop behavior

- RAF scroll moves duplicated track over **280 seconds** per full loop.
- Target readability: ~**5–8 seconds** per card in a typical 1200px viewport (depends on card count/width).
- Pause on `mouseenter` / `focusin`; resume after 200–600 ms when pointer/focus leaves.

## Mobile behavior (375×812, 390×844)

- `MOBILE_AUTO_SCROLL = false` → init adds `is-manual-only`, **no RAF auto tick**.
- User scrolls/swipes viewport horizontally only.

## Reduced motion

- `matchMedia('(prefers-reduced-motion: reduce)')` → no track clone, `is-manual-only`, no RAF.

## Manual QA checklist (Owner, staging after merge)

- [ ] Desktop: ticker readable ~5–8 s per card
- [ ] Desktop: hover pauses scroll
- [ ] Mobile 375×812: no auto-scroll; swipe works
- [ ] Mobile: focus on link pauses (keyboard)
- [ ] OS reduced motion: static/manual strip only
- [ ] Hard refresh / `?v=3` loads new JS

## Automated tests

```bash
python -m pytest tests/unit/test_competitions_ticker.py -q
python -m pytest tests/unit/test_events_public_routes.py::TestTickerLinks -q
```

No JS unit tests for scroll speed (manual QA required).

## Production

Not deployed. `main` unchanged until GM approval.
