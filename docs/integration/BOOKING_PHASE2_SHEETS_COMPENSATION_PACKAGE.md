# BOOKING_PHASE2 — Partial Sheets Compensation (B + E)

**Версия:** 1.0 (review)  
**Ветка:** `feature/booking-phase2-sheets-compensation`  
**Статус:** ready for review — **не мержить без GM approval**  
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

## Files changed

| File | Change |
|------|--------|
| `app/services/booking/pipeline.py` | `_write_sheets_journal`, `_compensate_partial_sheets_failure`, `SheetsBookingError` |
| `app/services/booking/sheets_writer.py` | `WORKOUT_STATUS_CANCELLED`, `compensate_workout_row()` |
| `app/services/booking/calendar_writer.py` | `delete_calendar_event_best_effort()` |
| `app/services/booking/__init__.py` | export `SheetsBookingError` |
| `app/routes/calendar_routes.py` | catch `SheetsBookingError` → 500 user message |
| `docs/operations/BOOKING_SHEETS_ORPHAN_CLEANUP_RUNBOOK.md` | Runbook E |
| `tests/unit/test_booking_sheets_compensation.py` | Partial failure + regression tests |

## Tests

```bash
python -m pytest tests/unit/test_booking_grid.py tests/unit/test_booking_pipeline_phase2.py \
  tests/unit/test_booking_features.py tests/unit/test_booking_calendar_v2.py \
  tests/unit/test_booking_calendar_reader_buffer.py tests/unit/test_booking_availability_phase2.py \
  tests/unit/test_booking_phase1.py tests/unit/test_booking_orchestrator_context.py \
  tests/unit/test_booking_service.py tests/unit/test_boat_slots.py \
  tests/unit/test_booking_sheets_compensation.py -q
```

**Expected:** 85 passed (81 booking suite + 4 compensation).

| Test | Asserts |
|------|---------|
| `test_client_workout_fail_compensates_workout_and_calendar` | compensation + calendar delete called |
| `test_calendar_fail_still_no_sheets` | Calendar fail → no Sheets, no compensation |
| `test_success_no_compensation` | happy path unchanged |
| `test_marks_workout_status_cancelled` | `compensate_workout_row` updates status + capacity |

## Merge gate

- [x] Unit test: Workouts written, Client_Workouts fails → compensated
- [x] Runbook E documented
- [x] No regression Phase 1 / flags OFF (85 passed locally)
- [ ] CI green on PR
- [ ] Owner review runbook

## Rollback plan

1. Revert PR commit on branch / hotfix revert on main after merge.
2. No DB migration; no `.env` changes.
3. Compensation is additive — rollback restores pre-B behavior (orphan risk on partial failure returns).
4. Production: **no deploy** until separate GM approval after staging E2E.

## Constraints (this PR)

- Production flags OFF — unchanged
- `.env` — not modified
- `mywave-node.service` — not touched
- `mywave-telegram-bot.service` — not touched
- TGbotAdmin — not touched
- No production restart / deploy

## Out of scope

- PR #17 (merged, prod GREEN)
- Production flags ON
- Staging E2E package (next track)
