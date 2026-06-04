# BOOKING_PHASE2 — Partial Sheets Compensation (B + E)

**Версия:** 0.1 (planning)  
**Ветка:** `feature/booking-phase2-sheets-compensation`  
**Статус:** planning — **не в PR #17**  
**Базовый документ:** [`BOOKING_PARTIAL_SHEETS_FOLLOWUP.md`](BOOKING_PARTIAL_SHEETS_FOLLOWUP.md)

---

## Scope

| Item | Description |
|------|-------------|
| **B** | Compensating delete при partial Sheets failure после успешного `write_workout_row()` |
| **E** | Runbook: поиск orphan `Workouts` без пары в `Client_Workouts` |

## Target scenario (test)

```text
write_workout_row()     → OK
write_client_workout_row() → FAIL
→ Workouts row удалён / помечен (compensation)
→ Calendar event best-effort delete (existing pipeline pattern)
→ user sees error, no orphan Workouts
```

## Out of scope

- PR #17 merge / prod flags ON
- TGbotAdmin, Node, telegram-bot systemd
- Production deploy без отдельного approval

## Files (planned)

| File | Change |
|------|--------|
| `app/services/booking/pipeline.py` | try/except + compensation |
| `app/services/booking/sheets_writer.py` | delete/mark helper |
| `docs/operations/BOOKING_SHEETS_ORPHAN_CLEANUP_RUNBOOK.md` | Runbook E |
| `tests/unit/test_booking_sheets_compensation.py` | Partial failure scenario |

## Merge gate

- [ ] Unit test: Workouts written, Client_Workouts fails → compensated
- [ ] Runbook reviewed by Owner
- [ ] No regression Phase 1 / flags OFF
- [ ] Separate PR, CI green
