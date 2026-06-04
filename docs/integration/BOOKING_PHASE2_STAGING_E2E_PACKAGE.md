# BOOKING_PHASE2_STAGING_E2E — Planning Package

**Версия:** 1.0
**Дата:** 2026-06-04
**Статус:** planning — execution **после PR4 merge + staging deploy**
**Prod baseline:** PR #16 GREEN, flags OFF (`cf318cdc`)

**Participants:** Site Owner + TGbotAdmin + (optional) QA

**Prerequisite decisions:**

- [x] TGbotAdmin round 2 PASS (PR #16)
- [x] Owner boat grid: **Site sync to 07:00–19:30** (PR4)
- [ ] PR4 merged + deployed to staging
- [ ] Test Calendar ID + test Spreadsheet ID from Owner
- [ ] Staging URL / instance from Owner

---

## 1. Staging environment

### 1.1 Options (Owner chooses)

| Option | Path | Notes |
|--------|------|-------|
| A | Dedicated `/var/www/mywave-staging` + `mywave-staging.service` | Isolated; preferred for E2E |
| B | Prod host, test Calendar/Sheet IDs in `.env.staging` | Lower infra cost |
| C | Local + ngrok | Dev-only smoke |

**Deferred in PR2** — revisit now that PR3+PR4 backend/UI exist.

### 1.2 Required staging config

```bash
# Feature flags — ALL ON for E2E
BOOKING_PHASE2_AVAILABILITY=1
BOOKING_PHASE2_TRAVEL_BUFFER=1
BOOKING_PHASE2_MULTI_SET_BOAT=1
BOOKING_PHASE2_SUMMARY_V2=1
BOOKING_PHASE2_GYM_LOCATION_V2=1

# Isolated Google resources (NOT production IDs)
GOOGLE_CALENDAR_ID=<staging_test_calendar>@group.calendar.google.com
SPREADSHEET_ID=<staging_test_spreadsheet>

# Canonical domain unchanged
SERVER_NAME=https://mywavewake.ru  # or staging URL
TIMEZONE=Europe/Moscow
```

**Restart policy on staging:** `mywave-site` (or `mywave-staging`) only — **not** node / telegram-bot unless Owner approves joint test.

---

## 2. Smoke scenarios — PR3 (backend)

From [`BOOKING_PHASE2_PR3_IMPLEMENTATION_PACKAGE.md`](BOOKING_PHASE2_PR3_IMPLEMENTATION_PACKAGE.md) §6.4:

| ID | Check |
|----|-------|
| P3-1 | POST boat 1 set → 1 event 30min, summary v2 |
| P3-2 | POST boat 3 sets → 1 event 90min, `set_count=3` |
| P3-3 | POST gym 4th client OK, 5th → **409** |
| P3-4 | POST boat on occupied slot → **409**, no Sheets orphan |
| P3-5 | Calendar insert between GET and POST → **409** |
| P3-6 | Duplicate POST same range → 400 idempotency |
| P3-7 | Flags OFF clone → Phase 1 POST unchanged |

---

## 3. Smoke scenarios — PR4 (frontend)

| ID | Check |
|----|-------|
| P4-1 | Boat UI: slots only **07:00–19:30** window |
| P4-2 | Slot with `max_set_count=3` → picker 1..3 |
| P4-3 | Preview `18:00–19:30` for 3 sets |
| P4-4 | Button `Подтвердить: 3 сета (18:00–19:30)` |
| P4-5 | POST payload includes `set_count: 3` |
| P4-6 | Flags OFF regression: no picker, Phase 1 POST |

---

## 4. Joint TGbotAdmin checklist

| ID | Check |
|----|-------|
| J1 | Web POST creates event bot sees as busy |
| J2 | Bot POST + Site POST race → one wins, other 409 |
| J3 | Gym 4/4 both sides |
| J4 | Multi-set 18:00–19:30 continuous (Site web) |
| J5 | WEB_ID / `(ID: tg_id)` separation |
| J6 | Boat grid alignment: no Site slots outside 07:00–19:30 |
| J7 | Travel buffer cross-day (evening boat → morning gym) |
| J8 | Location v2: `Зал`, `Катер` in Calendar |

---

## 5. Full checklist reference

Detailed steps: [`BOOKING_PHASE2_STAGING_SMOKE.md`](BOOKING_PHASE2_STAGING_SMOKE.md)

Sections to execute in order:

1. Preconditions + flags ON
2. Phase 1 regression (flags OFF clone optional)
3. Gym capacity + confirmation UX
4. Boat single + multi-set
5. Travel buffer
6. Pre-confirm recheck / 409
7. TGbotAdmin cross-smoke
8. Logs (no PII)
9. Production rollout gate (**not** in this session)

---

## 6. Test data conventions

| Field | Staging value |
|-------|---------------|
| Web booking phone | `+7999000XXXX` test range |
| Name | `Staging Test N` |
| WEB_ID | `(WEB_ID: bk_…)` in summary |
| Telegram test | TGbotAdmin test user only |

**Do not** use production PII or prod Telegram channels.

---

## 7. Evidence to collect

Owner / Site deliver after staging run:

1. Staging URL + git HEAD
2. Flags snapshot (`get_booking_phase2_flags()`)
3. Screenshots: multi-set UI, confirm button, success modal
4. Calendar event links (boat 1-set, boat 3-set, gym)
5. Sheets rows count (Workouts + Client_Workouts)
6. 409 race test log (request/response, no orphan rows)
7. TGbotAdmin sign-off: PASS / issues
8. pytest on staging host: `75+ passed`

---

## 8. Go / No-Go gates

| Gate | Criteria |
|------|----------|
| **Staging GREEN** | P3-* + P4-* + J-* all pass |
| **Prod flags ON** | Separate GM approval; one flag at a time per STAGING_SMOKE §10 |
| **Phase 2 complete** | Staging GREEN + PR4 prod + flags ON approval + Partial Sheets follow-up status |

---

## 9. Timeline (suggested)

| Step | Owner | Site |
|------|-------|------|
| 1 | Provide test Calendar/Sheet + staging instance | PR4 merge |
| 2 | — | Deploy staging, flags ON |
| 3 | Execute joint smoke with TGbotAdmin | Support / fixes |
| 4 | Sign-off staging GREEN | Release package |
| 5 | Approve phased prod flags | Deploy flags OFF until approved |

---

## 10. References

- PR16 prod record: [`BOOKING_PHASE2_PR16_MERGE_PACKAGE.md`](BOOKING_PHASE2_PR16_MERGE_PACKAGE.md) §9
- PR4 scope: [`BOOKING_PHASE2_PR4_IMPLEMENTATION_PACKAGE.md`](BOOKING_PHASE2_PR4_IMPLEMENTATION_PACKAGE.md)
- Partial Sheets: [`BOOKING_PARTIAL_SHEETS_FOLLOWUP.md`](BOOKING_PARTIAL_SHEETS_FOLLOWUP.md)
