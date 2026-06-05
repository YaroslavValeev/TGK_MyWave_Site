# BOOKING_PHASE2 — Partial Sheets Compensation (B + E)

**Версия:** 1.2 (TGbotAdmin whitespace cleanup)
**Ветка:** `feature/booking-phase2-sheets-compensation`
**PR:** https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/18
**Статус:** APPROVED FOR CODE REVIEW ONLY — **не мержить / не деплоить без merge approval**
**Базовый документ:** [`BOOKING_PARTIAL_SHEETS_FOLLOWUP.md`](BOOKING_PARTIAL_SHEETS_FOLLOWUP.md)

---

## Scope

| Item | Description |
|------|-------------|
| **B** | Compensating delete при partial Sheets failure после успешного `write_workout_row()` |
| **E** | Runbook: поиск orphan `Workouts` без пары в `Client_Workouts` |

## Compensation strategy (Option B)

**Trigger:** `write_workout_row()` succeeded, `write_client_workout_row()` raised.

**Steps (best-effort, in `_compensate_partial_sheets_failure`):**

1. `compensate_workout_row(workout_id)` — mark `Workouts.workout_status=cancelled`, `current_capacity=0` via `update_record` (no physical row delete; audit-friendly).
2. `delete_calendar_event_best_effort(event_id)` — remove Calendar event created in same transaction.
3. Log `booking_sheets_partial_failure` with `compensation` flags (no PII).
4. Raise `SheetsBookingError` → HTTP 500 «Не удалось завершить запись» for web booking.

**Not compensated:** if Calendar insert fails — Sheets never written (existing behavior).

---

## GM verification matrix

| # | Scenario | Confirmed by | Result |
|---|----------|--------------|--------|
| 1 | `write_client_workout_row()` fails → compensation called; Workouts marked cancelled; Calendar delete best-effort | `test_client_workout_fail_compensates_workout_and_calendar`, `test_marks_workout_status_cancelled` | ✅ |
| 2 | Compensation mark fails → logged (`workout_row_mark_failed`); `SheetsBookingError` raised; no silent success | `test_compensation_mark_fail_still_raises_sheets_error` | ✅ |
| 3 | Calendar delete fails → logged (`calendar_delete_failed`); user gets error; `workout_id_tail` in log for incident | `test_calendar_delete_fail_still_raises_sheets_error` | ✅ |
| 4 | Happy path → no compensation; Calendar + both Sheets rows written | `test_success_no_compensation`, `test_web_booking_creates_calendar_then_sheets` | ✅ |
| 5 | Calendar fail → no Sheets writes; no compensation | `test_calendar_fail_still_no_sheets`, `test_calendar_failure_no_sheets` | ✅ |

**Log correlation fields (no PII):** `workout_id_tail`, `compensation`, `workouts_written`, `client_workouts_written`, `error`.

**Incident recovery:** runbook [`BOOKING_SHEETS_ORPHAN_CLEANUP_RUNBOOK.md`](../operations/BOOKING_SHEETS_ORPHAN_CLEANUP_RUNBOOK.md) — search by `workout_id` / Calendar `event_id`.

---

## Files changed

| File | Change |
|------|--------|
| `app/services/booking/pipeline.py` | `_write_sheets_journal`, `_compensate_partial_sheets_failure`, `SheetsBookingError` |
| `app/services/booking/sheets_writer.py` | `WORKOUT_STATUS_CANCELLED`, `compensate_workout_row()` |
| `app/services/booking/calendar_writer.py` | `delete_calendar_event_best_effort()` |
| `app/services/booking/__init__.py` | export `SheetsBookingError` |
| `app/routes/calendar_routes.py` | catch `SheetsBookingError` → 500 user message |
| `docs/operations/BOOKING_SHEETS_ORPHAN_CLEANUP_RUNBOOK.md` | Runbook E |
| `tests/unit/test_booking_sheets_compensation.py` | 6 tests (GM matrix) |
| `docs/integration/BOOKING_PHASE2_SHEETS_COMPENSATION_PACKAGE.md` | this package |

---

## Tests

```bash
python -m pytest tests/unit/test_booking_grid.py tests/unit/test_booking_pipeline_phase2.py \
  tests/unit/test_booking_features.py tests/unit/test_booking_calendar_v2.py \
  tests/unit/test_booking_calendar_reader_buffer.py tests/unit/test_booking_availability_phase2.py \
  tests/unit/test_booking_phase1.py tests/unit/test_booking_orchestrator_context.py \
  tests/unit/test_booking_service.py tests/unit/test_boat_slots.py \
  tests/unit/test_booking_sheets_compensation.py -q
```

**Expected:** 87 passed (81 booking suite + 6 compensation).

| Test | GM # | Asserts |
|------|------|---------|
| `test_client_workout_fail_compensates_workout_and_calendar` | 1 | compensation + calendar delete called; SheetsBookingError |
| `test_marks_workout_status_cancelled` | 1 | Workouts row → `cancelled`, capacity 0 |
| `test_compensation_mark_fail_still_raises_sheets_error` | 2 | log `workout_row_mark_failed`; no success |
| `test_calendar_delete_fail_still_raises_sheets_error` | 3 | log `calendar_delete_failed`; workout_id_tail |
| `test_success_no_compensation` | 4 | happy path unchanged |
| `test_calendar_fail_still_no_sheets` | 5 | Calendar fail → no Sheets, no compensation |

---

## Merge gate

- [x] GM scenarios 1–5 covered by tests
- [x] Runbook E documented
- [x] No regression Phase 1 / flags OFF
- [ ] CI green on PR head
- [ ] Merge approval (separate from code review)

---

## Rollback plan

1. Revert PR commit on branch / hotfix revert on main after merge.
2. No DB migration; no `.env` changes.
3. Rollback restores pre-B behavior (orphan risk on partial failure returns).
4. Production: **no deploy** until separate GM approval after staging E2E.

---

## Constraints (confirmed)

| Constraint | Status |
|------------|--------|
| Production flags OFF | ✅ unchanged |
| `.env` not modified | ✅ |
| TGbotAdmin not touched | ✅ |
| `mywave-node.service` not touched | ✅ |
| `mywave-telegram-bot.service` not touched | ✅ |
| `mywave-site` not restarted | ✅ |
| Production deploy | ❌ not performed |

---

## Out of scope

- Production flags ON
- Staging E2E package (next track after merge approval)
