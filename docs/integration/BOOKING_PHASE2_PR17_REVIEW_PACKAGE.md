# BOOKING_PHASE2_PR17 — Review Package (merge gate)

**Версия:** 1.0  
**Дата:** 2026-06-04  
**Статус:** APPROVED FOR CODE REVIEW ONLY — merge после TGbotAdmin + Owner  
**PR:** https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/17  
**Branch:** `feature/booking-phase2-pr4-frontend-multiset`  
**Commit:** `8f9a07f0bc6045911c6e264e2342b9248edae8af`

**Связанные документы:**

- [`BOOKING_PHASE2_PR4_IMPLEMENTATION_PACKAGE.md`](BOOKING_PHASE2_PR4_IMPLEMENTATION_PACKAGE.md)
- [`BOOKING_PARTIAL_SHEETS_FOLLOWUP.md`](BOOKING_PARTIAL_SHEETS_FOLLOWUP.md) — отдельный PR (ветка `feature/booking-phase2-sheets-compensation`)

---

## 1. Executive summary

| Item | Value |
|------|--------|
| Scope | PR4 frontend multi-set + boat grid 07:00–19:30 |
| CI | **GREEN** — workflow `CI`, job `quality-checks` SUCCESS |
| Tests (local booking suite) | **81 passed** (см. §6) |
| Prod deploy | **не выполнять** до merge approval |
| Flags ON | **не включать** до staging E2E + отдельного GM approval |

---

## 2. Final file list (commit `8f9a07f0`)

| File | Role |
|------|------|
| `app/config/booking_grid.py` | Canonical `BOAT_GRID_START=07:00`, `BOAT_GRID_END=19:30` |
| `app/services/booking/availability.py` | Import grid constants (Phase 2 engine) |
| `app/routes/calendar_routes.py` | Legacy `get_boat_slots()` grid sync |
| `static/js/booking.js` | Multi-set UI, POST `set_count`, 409, flags OFF regression |
| `templates/partials/booking_modals.html` | `#boatSetPicker` DOM |
| `static/css/style.css` | Set-picker styles |
| `tests/unit/test_booking_grid.py` | Grid constants |
| `tests/unit/test_boat_slots.py` | Grid boundaries + hide full |

---

## 3. UI evidence (screenshots / video)

### 3.1 Автоматизированный reference (local, без staging)

Откройте в браузере:

`docs/integration/evidence/PR17_ui_reference.html`

Рекомендуемые скриншоты (приложить к PR comment или wiki):

| # | Сценарий | Panel ID в HTML |
|---|----------|-----------------|
| 1 | Катер 1 сет + кнопка подтверждения | `#s1` |
| 2 | Катер 3 сета + preview + кнопка | `#s2` |
| 3 | Flags OFF — «Подтвердить запись», без picker | `#s3` |
| 4 | Grid 07:00 … 19:30 | `#s4` |
| 5 | 409 flow (описание UX) | `#s5` |

### 3.2 Staging / local с реальным API (рекомендуется Owner)

**Flags ON (multi-set UI):**

```bash
export BOOKING_PHASE2_AVAILABILITY=1
export BOOKING_PHASE2_MULTI_SET_BOAT=1
export BOOKING_PHASE2_SUMMARY_V2=1
# restart only mywave-site on staging
```

1. Открыть сайт → «Запись на катер» → дата с свободными слотами.
2. **1 сет:** слот с `max_set_count: 1` → шаг 4 → кнопка `Подтвердить: 1 сет (HH:MM–HH:MM)`.
3. **2–3 сета:** слот с `max_set_count >= 3` → picker → preview `HH:MM–HH:MM (N сета)` → подтверждение.
4. **409:** два параллельных бронирования на один слот (или mock busy) → toast + возврат на шаг 2, слоты обновлены.

**Flags OFF (prod сегодня):**

```bash
# все BOOKING_PHASE2_* unset или =0
```

- Нет `#boatSetPicker`
- Кнопка «Подтвердить запись»
- DevTools → POST `/api/calendar/book` — тело **без** `set_count`

### 3.3 Видео (опционально)

30–60 с: выбор даты → слот → (picker) → контакты → confirm → success modal.

---

## 4. Grid evidence

### 4.1 Machine-readable dump

См. [`evidence/PR17_grid_slots.txt`](evidence/PR17_grid_slots.txt):

```text
count=26
first=07:00
last=19:30
has_0600=False
has_0700=True
has_1930=True
has_2000=False
has_2100=False
```

### 4.2 Unit test

`tests/unit/test_boat_slots.py::test_boat_slots_grid_boundaries` — asserts first/last и отсутствие 06:00 / 20:00 / 21:00.

### 4.3 API check (staging/local)

```bash
curl -s "https://<staging-host>/api/calendar/slots/2026-06-15?service=boat" \
  -H "X-CSRFToken: <token>" --cookie "session=..." | jq '[.[].time] | [first, last]'
# Ожидание: ["07:00", "19:30"] при пустом дне (flags OFF legacy path)
```

---

## 5. Flags OFF regression — подтверждение

| Check | Implementation |
|-------|----------------|
| Нет picker | `boatSlotHasMaxSetCount` false если API не вернул `max_set_count`; `#boatSetPicker` hidden |
| POST без `set_count` | `finalRequestData.set_count` только при `boatSlotHasMaxSetCount` |
| Кнопка обычная | `updateFinalConfirmButtonLabel()` → «Подтвердить запись» |
| Phase 1 UX | Слот → сразу шаг 3; gym flow без изменений |

**Код:** `static/js/booking.js` — `handleBoatSlotSelected`, `updateFinalConfirmButtonLabel`, `submitBooking` (блок `finalRequestData`).

**Тесты:** `test_get_boat_slots_uses_sheets_when_flag_off`, `test_all_flags_off_by_default`, Phase 1 pipeline tests.

---

## 6. CI status

| Check | Result | URL |
|-------|--------|-----|
| `quality-checks` (CI) | **SUCCESS** | https://github.com/YaroslavValeev/TGK_MyWave_Site/actions/runs/26931739306 |

PR state: **OPEN**, review TGbotAdmin.

---

## 7. Test command and output

### 7.1 Full booking unit suite (81 tests)

```bash
cd Site_MyWave
python -m pytest \
  tests/unit/test_booking_grid.py \
  tests/unit/test_booking_pipeline_phase2.py \
  tests/unit/test_booking_features.py \
  tests/unit/test_booking_calendar_v2.py \
  tests/unit/test_booking_calendar_reader_buffer.py \
  tests/unit/test_booking_availability_phase2.py \
  tests/unit/test_booking_phase1.py \
  tests/unit/test_booking_orchestrator_context.py \
  tests/unit/test_booking_service.py \
  tests/unit/test_boat_slots.py \
  -q --tb=short
```

**Ожидаемый результат:** `81 passed`

### 7.2 Saved output

См. [`evidence/PR17_test_output.txt`](evidence/PR17_test_output.txt) (subset run; полный suite — команда выше).

### 7.3 PR4-focused subset

```bash
python -m pytest tests/unit/test_booking_grid.py tests/unit/test_boat_slots.py -v
```

---

## 8. Rollback / disable plan

### 8.1 До merge (code review)

- Закрыть PR #17 без merge — prod без изменений.

### 8.2 После merge + deploy (flags OFF)

| Action | Effect |
|--------|--------|
| Deploy revert commit | Откат UI + grid на предыдущую версию |
| Flags остаются OFF | Phase 2 pipeline/multi-set на backend не активен |
| Grid 07:00–19:30 | **Остаётся** после deploy даже при flags OFF (узкое окно слотов — Owner-approved) |

**Rollback команды (Owner, deploy window):**

```bash
cd /var/www/mywave
git fetch origin
git checkout <previous-main-sha>   # pre-PR17 merge
# rebuild static if needed
sudo systemctl restart mywave-site   # ONLY this unit
```

### 8.3 Disable без redeploy (runtime)

```bash
# .env — только на staging / по approval на prod
BOOKING_PHASE2_AVAILABILITY=0
BOOKING_PHASE2_MULTI_SET_BOAT=0
BOOKING_PHASE2_SUMMARY_V2=0
BOOKING_PHASE2_TRAVEL_BUFFER=0
BOOKING_PHASE2_GYM_LOCATION_V2=0
sudo systemctl restart mywave-site
```

**Не трогать:** `mywave-node`, `mywave-telegram-bot`, TGbotAdmin prod.

### 8.4 Partial Sheets gap

Orphan Workouts при partial failure — **не закрыт PR17**. Follow-up: `feature/booking-phase2-sheets-compensation` (Option B + runbook E).

---

## 9. Partial Sheets — next branch

| Item | Value |
|------|--------|
| Branch | `feature/booking-phase2-sheets-compensation` |
| Scope | Compensating delete (B) + cleanup runbook (E) |
| Blocker for PR17 merge? | **No** |
| Blocker for prod flags ON? | **Yes** (recommended) |

---

## 10. Merge gate checklist

- [x] PR4 scope code complete
- [x] CI green
- [x] 81 booking tests passed (local)
- [x] Grid evidence (file + unit test)
- [x] Flags OFF regression documented
- [x] UI reference HTML for screenshots
- [ ] TGbotAdmin review PASS
- [ ] Owner staging screenshots (optional, recommended)
- [ ] GM merge approval
- [ ] Deploy window + restart `mywave-site` only

---

## 11. Contacts / handoff

PR #17 передан на review **TGbotAdmin**.  
Site не мержит до отдельного approval.
