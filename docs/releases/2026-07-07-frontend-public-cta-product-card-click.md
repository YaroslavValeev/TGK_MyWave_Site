# Release — public CTA unify + product card click (PR97)

**Date:** 2026-07-07  
**Type:** frontend  
**PR:** [#97](https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/97)  
**Deploy SHA:** `43dc7ca2e7b6c660ce107db809d087882955a59a`  
**Rollback SHA:** `beb5c8ad1a2147e3424c277384397093e2461e05`  
**Result:** **PASS** (Owner visual QA)

---

## Summary

- Unified public CTA: white background, turquoise border `#00bcd4`, `border-radius: 10px`.
- Product cards in «Товары» trigger existing Buy button on card click/tap (no duplicated purchase logic).
- Cache bust: `public-cta1`, `product-card-click1`.

## Server smoke (2026-07-07)

| Check | Result |
|-------|--------|
| pytest (25 tests on server) | PASS |
| `mywave-site` restart | active (running) |
| `/health/live` | `{"live":true,"status":"ok"}` |
| `/health/ready` | `"status":"ok"` |
| Owner QA — buttons | PASS |
| Owner QA — product card click | PASS |
| Owner QA — Online Coaching CTA | PASS |

## Out of scope

- `.env` — not changed
- DB / Sheets schema — not changed
- TGbotAdmin / node — not restarted

## Also on `main` (same pull)

Online Coaching Phase 2 code merged earlier (`546703ca` lineage). **No new OC Phase 2 env flags enabled** unless Owner approves separately.

## Next (separate PRs)

1. Booking handoff A2/I1 — device QA
2. Online Coaching E2E sign-off
3. Android calendar export
4. Workouts.duration data hygiene (Sheets ops)
5. Notifications v2 runtime
6. Camp automation
