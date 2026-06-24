# PR53.4.1 — real mobile competitions carousel autoplay

## Root cause (PR53.4 partial fail)
`MOBILE_AUTO_SCROLL = true` was not enough: iOS/mobile Safari often ignores programmatic `scrollLeft` updates on `overflow-x: auto` containers. The ticker used `requestAnimationFrame` + `scrollLeft`, which works on desktop but not on real mobile.

## Fix
- Autoplay via **CSS `@keyframes` + `transform: translateX(-50%)`** on duplicated track
- Duration: `--ticker-duration: 840s` (same as desktop)
- Pause on touch/hover/focus via `animation-play-state: paused`
- Cache bust: `competitions-ticker.js/css?v=8`

## Tests
```bash
pytest tests/unit/test_pr534_1_carousel_autoplay.py \
       tests/unit/test_pr534_mobile_qa_followup.py \
       tests/unit/test_competitions_ticker.py -q

# E2E (playwright):
pytest tests/e2e/test_competitions_ticker_mobile_autoplay.py -m e2e
```

## Video evidence (390×844)
Capture after merge/staging:
```bash
python scripts/capture_ticker_mobile_evidence.py
```
Output: `docs/evidence/pr534_1/ticker-mobile-390x844.webm`

Or Owner manual: 10–15s screen recording, ticker moves without swipe.

Deploy status: **NOT STARTED**
