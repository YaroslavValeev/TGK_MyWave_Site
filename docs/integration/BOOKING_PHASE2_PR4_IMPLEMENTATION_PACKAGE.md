# BOOKING_PHASE2_PR4 — Implementation Package

**Версия:** 1.0
**Дата:** 2026-06-04
**Статус:** на approval GM → code review
**База prod:** PR #16 merged + deployed (`cf318cdc`), flags OFF — GREEN
**Owner decision (boat grid):** **синхронизировать Site с TGbotAdmin** → canonical **`07:00–19:30`**

**Связанные документы:**

- [`BOOKING_PHASE2_PR16_MERGE_PACKAGE.md`](BOOKING_PHASE2_PR16_MERGE_PACKAGE.md)
- [`BOOKING_PHASE2_STAGING_E2E_PACKAGE.md`](BOOKING_PHASE2_STAGING_E2E_PACKAGE.md)
- [`BOOKING_PARTIAL_SHEETS_FOLLOWUP.md`](BOOKING_PARTIAL_SHEETS_FOLLOWUP.md)
- [`BOOKING_CALENDAR_EVENT_CONTRACT_v2.md`](BOOKING_CALENDAR_EVENT_CONTRACT_v2.md)

---

## Executive summary

| PR | Scope | Prod сейчас |
|----|-------|-------------|
| PR #16 (PR3) | POST recheck + writer v2 + 409 | ✅ deployed, flags OFF |
| **PR4** | Frontend multi-set UI + boat grid sync + gym confirm UX | ⏳ этот пакет |
| Staging E2E | Joint smoke Site + TGbotAdmin | после PR4 deploy staging |

**PR4 закрывает:** UI `set_count`, range preview, confirm button text, flags OFF regression, **boat grid 07:00–19:30**.

**PR4 не закрывает:** staging E2E execution, prod flags ON, Partial Sheets transaction (см. follow-up doc).

---

## 0. Owner decisions (зафиксировано)

### Boat grid — canonical

| | Было (Site) | Canonical (Owner) |
|---|-------------|-------------------|
| Start | 06:00 | **07:00** |
| End | 21:00 | **19:30** |
| Source of truth | TGbotAdmin contract | **TGbotAdmin** |

**Scope PR4:** привести Site backend + frontend + docs к `07:00–19:30` **до staging E2E** (не prod flags ON).

---

## 1. Architecture

### 1.1 UX flow (boat, flags ON on staging)

```text
User selects date → GET boat slots (max_set_count per slot)
  → User picks start time
  → UI: set_count selector 1..max_set_count (adjacent only)
  → Preview: "15:00–16:30 (3 сета)"
  → Confirm button: "Подтвердить: 3 сетов (15:00–16:30)"
  → POST /api/calendar/book { set_count: 3, ... }
```

### 1.2 UX flow (flags OFF — production today)

```text
Same UI as Phase 1:
  - no set_count selector (implicit 1)
  - no max_set_count in API response
  - POST without set_count (default 1)
  - boat grid still 07:00–19:30 after PR4 backend sync (display only change at flags OFF)
```

### 1.3 Graceful degradation matrix

| Flag / API field | UI behavior |
|------------------|-------------|
| `BOOKING_PHASE2_MULTI_SET_BOAT=0` or no `max_set_count` | Single-set boat UX (Phase 1) |
| `max_set_count: 1` | Selector hidden or fixed at 1 |
| `max_set_count: N>1` | Selector 1..N |
| Gym | No set_count; optional success modal coords (existing / extend) |

---

## 2. File list (PR4)

### 2.1 Modified — backend (grid sync)

| File | Changes |
|------|---------|
| `app/services/booking/availability.py` | `BOAT_GRID_START=07:00`, `BOAT_GRID_END=19:30` (or import from config) |
| `app/config/booking_durations.py` or **new** `app/config/booking_grid.py` | Canonical `BOAT_GRID_START` / `BOAT_GRID_END` constants |
| `app/routes/calendar_routes.py` | Legacy Phase 1 boat slot generator: `06:00–21:00` → **07:00–19:30** |
| `docs/integration/BOOKING_AVAILABILITY_CONTRACT_v1.md` | § grid hours → 07:00–19:30 |
| `tests/unit/test_booking_availability_phase2.py` | Update grid edge tests |
| `tests/unit/test_boat_slots.py` | Update slot count expectations if needed |

### 2.2 Modified — frontend

| File | Changes |
|------|---------|
| `static/js/booking.js` | set_count state, selector, range preview, POST payload, confirm button text |
| `templates/partials/booking_modals.html` (or inline in `index.html`) | DOM for set picker + preview (if not JS-only) |
| `static/css/style.css` | Minimal set-picker styles (only if needed) |

### 2.3 New tests

| File | Purpose |
|------|---------|
| `tests/unit/test_booking_grid.py` | Canonical grid constants 07:00–19:30 |
| `tests/ui/test_booking_multiset.py` (optional) | Playwright: selector visible when `max_set_count>1` mock |

### 2.4 Not in PR4

| | PR / phase |
|---|-----|
| Production flags ON | Staging → separate GM approval |
| Partial Sheets transaction | Follow-up doc |
| TGbotAdmin code | — |
| `mywave-node` / telegram-bot systemd | — |

---

## 3. Frontend specification

### 3.1 State (boat)

```javascript
// After slot time selected:
selectedSlotTime = "15:00"
maxSetCount = slot.max_set_count || 1   // from GET response
setCount = 1                            // user choice, 1..maxSetCount
```

### 3.2 Range preview helper

```javascript
function formatBoatRangePreview(startTime, setCount) {
  // start + setCount * 30 min → "HH:MM–HH:MM"
  // label: "3 сета" / "1 сет" (match backend pluralization or simple RU rules)
}
```

### 3.3 Confirm button (required text)

```text
Подтвердить: N сетов (HH:MM–HH:MM)
```

Examples:

- `Подтвердить: 1 сет (18:00–18:30)`
- `Подтвердить: 3 сетов (18:00–19:30)`

**Note:** Owner spec uses «сетов» in template; align pluralization with contract v2 (`1 сет`, `2 сета`, `3 сета`, `5 сетов`) — recommend:

```text
Подтвердить: {setsLabel} ({start}–{end})
```

where `setsLabel` = `format_boat_sets_label(N)` equivalent in JS.

### 3.4 POST payload extension

```json
{
  "service_type": "boat",
  "date": "2026-06-15",
  "time": "18:00",
  "set_count": 3,
  "name": "...",
  "phone": "+7..."
}
```

Only send `set_count` when `service === 'boat'` and user selected N>1 or always send `set_count: 1` for boat (backend accepts both).

### 3.5 409 handling (PR3 backend ready)

Map HTTP 409 responses to user-friendly Russian (already in `calendar_routes`):

- boat occupied → refresh slots message
- gym full → choose another time

Frontend: on 409, reload slots for selected date.

### 3.6 Flags OFF regression

- No `max_set_count` in API → hide set picker
- POST unchanged (no `set_count` or `set_count: 1`)
- No JS console errors
- Existing gym flow unchanged

---

## 4. Backend grid sync (PR4 prerequisite)

### 4.1 Single source of truth

```python
# app/config/booking_grid.py (proposed)
BOAT_GRID_START = time(7, 0)
BOAT_GRID_END = time(19, 30)
```

Import in `availability.py` and `calendar_routes.py` — **no duplicate 06:00/21:00**.

### 4.2 Last bookable slot

With 30-min sets, last **start** at 19:30 → end 20:00 (1 set) or last multi-set start computed by `compute_max_set_count`.

Verify: 19:30 start + 1 set = 19:30–20:00 — confirm TGbotAdmin allows end after 19:30 grid label (grid = operating hours for **starts**).

---

## 5. Test plan

### 5.1 Unit

| Test | Assert |
|------|--------|
| `test_boat_grid_canonical` | 07:00 / 19:30 constants |
| `test_build_boat_slots_respects_grid` | No slot before 07:00 or after 19:30 start rules |
| `test_flags_off_boat_slots_count` | Phase 1 path slot count matches new grid |
| Regression | Full booking suite **75+ passed** |

### 5.2 Manual / staging (after PR4 deploy staging, flags ON)

| # | Check |
|---|-------|
| M1 | Boat slot 18:00 shows max_set_count > 1 when adjacent free |
| M2 | Select 3 sets → preview 18:00–19:30 |
| M3 | Confirm button text matches spec |
| M4 | POST creates 1 Calendar event 90 min |
| M5 | Flags OFF prod clone → Phase 1 UX, no picker |

---

## 6. Risk assessment

| Risk | Mitigation |
|------|------------|
| Grid change shrinks bookable window | Owner-approved; communicate in release notes |
| JS breaks Phase 1 | Feature-detect `max_set_count`; tests flags OFF |
| Wrong end time in preview | Unit test JS helper or shared duration constant comment |
| CSRF / modal regression | Existing flow unchanged; manual smoke |

---

## 7. Rollout plan

### Phase A — PR4 merge + prod deploy (flags OFF)

Same policy as PR #16: code on prod, **all flags OFF**, restart **only** `mywave-site`.

Grid sync affects displayed slots even at flags OFF (narrower window — intentional).

### Phase B — Staging E2E

See [`BOOKING_PHASE2_STAGING_E2E_PACKAGE.md`](BOOKING_PHASE2_STAGING_E2E_PACKAGE.md).

### Phase C — Prod flags ON

Separate GM approval after staging green.

---

## 8. Definition of Done

- [ ] GM approval this package
- [ ] Boat grid 07:00–19:30 Site-wide (backend + legacy routes)
- [ ] Multi-set UI behind `max_set_count` / flags
- [ ] Confirm button: `Подтвердить: … (HH:MM–HH:MM)`
- [ ] POST sends `set_count` for boat
- [ ] Flags OFF regression tests green
- [ ] CI green
- [ ] Staging E2E package ready (not executed in PR4)

---

## 9. Estimate

| Item | Days |
|------|------|
| Grid sync + tests | 0.5 |
| booking.js multi-set UI | 1.5–2 |
| Modal/CSS + 409 UX | 0.5 |
| Tests + manual QA prep | 0.5 |
| **Total PR4** | **3–3.5 days** |

---

## 10. Git workflow

```text
main @ cf318cdc (PR #16 prod)
  └── feature/booking-phase2-pr4-frontend-multiset
        └── PR → main
```

**Branch name (proposed):** `feature/booking-phase2-pr4-frontend-multiset`
