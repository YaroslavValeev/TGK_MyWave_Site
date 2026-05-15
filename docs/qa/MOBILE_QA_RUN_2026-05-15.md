# Mobile QA Run — MyWaveWake

**Date:** 2026-05-15  
**Production:** https://mywavewake.ru  
**Runtime baseline:** `3de56f8c` FROZEN  
**Frontend baseline:** `48dc9c64`  
**Canonical matrix:** [MOBILE_QA_MATRIX.md](MOBILE_QA_MATRIX.md)  
**Status:** **Step 1 — manual device QA** (Step 0 + precheck closed)  
**Precheck:** [MOBILE_QA_AUTOMATED_PRECHECK_2026-05-15.md](MOBILE_QA_AUTOMATED_PRECHECK_2026-05-15.md) · fix `3ae20741`

> Frontend deploy **governance-incomplete** без PASS в матрице + screenshots + smoke.

---

## Automated pre-check (2026-05-15, remote)

| Check | Result |
|-------|--------|
| `production_smoke.sh` | **PASS** |
| Key pages HTTP 200 | **PASS** |
| `mobile-home.css` static | **PASS** |
| Home HTML `?v=3` | **PASS** — after `systemctl restart mywave-site` |

**Step 0 closed.** Proceed to manual device QA (A1/A2/I1/T1).

Script: `bash scripts/qa_mobile_precheck.sh`

---

## Before testing

- [ ] Инкогнито / private mode  
- [ ] `mobile-home.css?v=3` (или новее) в Network  
- [ ] Не менять runtime · не restart Gunicorn для CSS  
- [ ] При FAIL: screenshot + browser + viewport + section  

Screenshots: `docs/qa/screenshots/2026-05-15/`

---

## Devices

| ID | Device | Browser | Required |
|----|--------|---------|----------|
| A1 | Android phone | Chrome | yes |
| A2 | Android phone | Yandex Browser | yes |
| I1 | iPhone | Safari | yes |
| T1 | Tablet | Chrome / Safari | yes |

---

## A1 — Android Chrome

| Section | Result | Screenshot | Notes |
|---------|--------|------------|-------|
| Hero | PENDING | `screenshots/2026-05-15/A1-hero.png` | compact, no giant whitespace |
| Services carousel | PENDING | `A1-services.png` | swipe, snap |
| Contacts | PENDING | `A1-contacts.png` | form visible |
| Chat button | PENDING | `A1-chat.png` | no CTA overlap |
| Reviews | PENDING | `A1-reviews.png` | avatars |
| Checklist | PENDING | `A1-checklist.png` | `/wake-industry/checklist` |
| Booking modal | PENDING | `A1-booking.png` | slots/date/close |
| Blog | PENDING | `A1-blog.png` | list/empty/cards |
| Navigation | PENDING | `A1-nav.png` | menu/anchors |
| Footer | PENDING | `A1-footer.png` | safe-area |

---

## A2 — Android Yandex Browser

| Section | Result | Screenshot | Notes |
|---------|--------|------------|-------|
| Hero | PENDING | `A2-hero.png` | |
| Services carousel | PENDING | `A2-services.png` | |
| Contacts | PENDING | `A2-contacts.png` | |
| Chat button | PENDING | `A2-chat.png` | |
| Reviews | PENDING | `A2-reviews.png` | |
| Checklist | PENDING | `A2-checklist.png` | |
| Booking modal | PENDING | `A2-booking.png` | |
| Blog | PENDING | `A2-blog.png` | |
| Navigation | PENDING | `A2-nav.png` | |
| Footer | PENDING | `A2-footer.png` | |

---

## I1 — iPhone Safari

| Section | Result | Screenshot | Notes |
|---------|--------|------------|-------|
| Hero | PENDING | `I1-hero.png` | safe-area top |
| Services carousel | PENDING | `I1-services.png` | momentum |
| Contacts | PENDING | `I1-contacts.png` | font ≥16px |
| Chat button | PENDING | `I1-chat.png` | home indicator |
| Reviews | PENDING | `I1-reviews.png` | |
| Checklist | PENDING | `I1-checklist.png` | |
| Booking modal | PENDING | `I1-booking.png` | |
| Blog | PENDING | `I1-blog.png` | |
| Navigation | PENDING | `I1-nav.png` | |
| Footer | PENDING | `I1-footer.png` | safe-area bottom |

---

## T1 — Tablet

| Section | Result | Screenshot | Notes |
|---------|--------|------------|-------|
| Hero | PENDING | `T1-hero.png` | |
| Services carousel | PENDING | `T1-services.png` | |
| Contacts | PENDING | `T1-contacts.png` | |
| Chat button | PENDING | `T1-chat.png` | |
| Reviews | PENDING | `T1-reviews.png` | |
| Checklist | PENDING | `T1-checklist.png` | |
| Booking modal | PENDING | `T1-booking.png` | |
| Blog | PENDING | `T1-blog.png` | |
| Navigation | PENDING | `T1-nav.png` | |
| Footer | PENDING | `T1-footer.png` | |

---

## Global criteria

| Criterion | Status |
|----------|--------|
| No horizontal scroll | PENDING |
| Touch targets ≥ 44px | PENDING |
| Typography readable | PENDING |
| Chat vs CTA | PENDING |
| Booking modal | PENDING |
| Blog HTTP 200 | **PASS** (automated) |
| Home HTML mobile-home v=3 | **FAIL** (prod v=2) |

---

## Final sign-off

| Field | Value |
|-------|-------|
| Tester | _заполнить после прогона_ |
| Commit tested | |
| CSS version | `mobile-home.css?v=3` |
| Overall result | **PENDING** |
| Ready for release gate | **NO** (until PASS) |

После прогона: скопировать PASS/FAIL в [MOBILE_QA_MATRIX.md](MOBILE_QA_MATRIX.md).
