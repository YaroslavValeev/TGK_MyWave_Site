# BOOKING_PARTIAL_SHEETS — Follow-up Package

**Версия:** 1.0
**Дата:** 2026-06-04
**Статус:** planning — **не blocker** для PR #16 merge / PR4
**Target:** resolve **до production flags ON** (recommended)

---

## 1. Problem statement

### Current pipeline order (PR #16)

```text
1. idempotency
2. assert_booking_available (flags ON)
3. client resolve
4. Calendar insert → event.id
5. write_workout_row(Workouts)
6. write_client_workout_row(Client_Workouts)
```

### Gap

| Failure point | Calendar | Workouts | Client_Workouts |
|---------------|----------|----------|-----------------|
| Recheck fail | — | — | — |
| Calendar fail | — | — | — |
| **Workouts OK, Client_Workouts fail** | ✅ event exists | ✅ row | ❌ missing |

**Result:** orphan `Workouts` row referencing valid `workout_id` without client linkage.

**Accepted for PR #16 merge** — documented non-blocker. **Must address before prod flags ON** (Owner + GM).

---

## 2. Impact

| Area | Impact |
|------|--------|
| Idempotency | May not detect dup by phone if only Workouts exists |
| Reporting | Workout appears without client |
| TGbotAdmin | May see Calendar event; Sheets inconsistent |
| Cleanup | Manual ops burden |

**Frequency:** low (Sheets append rarely fails mid-pipeline) — but high severity for data integrity.

---

## 3. Options (Owner pick)

### Option A — Reorder writes (minimal)

Write **Client_Workouts first** with pending status, then Workouts, then confirm — **not recommended** (Workouts is canonical schedule row).

### Option B — Compensating delete (recommended MVP)

```python
try:
    write_workout_row(...)
    write_client_workout_row(...)
except Exception:
    if event_id:
        delete_calendar_event(event_id)  # best-effort
    if workout_row_written:
        delete_or_mark_workout_row(workout_id)  # best-effort
    raise
```

**Pros:** no schema change; fixes orphan Workouts.
**Cons:** Calendar event deleted on Client_Workouts fail (user sees error — correct).

### Option C — Two-phase status field

Add `workout_status: pending|confirmed` in Workouts; finalize after both writes.

**Pros:** audit trail.
**Cons:** Sheets schema / TGbotAdmin awareness.

### Option D — Outbox / repair job

Async worker scans orphan Workouts (no Client_Workouts within N min) → alert + auto-delete or link.

**Pros:** handles delayed failures.
**Cons:** infra complexity.

### Option E — Documented cleanup only (minimum)

Runbook for ops: grep orphan `workout_id`, manual delete Workouts row + optional Calendar cancel.

**Pros:** zero code now.
**Cons:** does not meet «before flags ON» recommendation alone — combine with B or D.

---

## 4. Recommended path

| Phase | Action | When |
|-------|--------|------|
| **PR4.x or PR5** | Option **B** compensating delete + structured log | Before staging E2E |
| **Staging** | Inject fault test: mock `append_dict_to_sheet` fail on Client_Workouts | Staging E2E |
| **Before prod flags ON** | Option **E** runbook in ops docs | GM approval gate |
| **Later** | Option **D** repair job if ops load justifies | Post Phase 2 |

---

## 5. Proposed implementation sketch (Option B)

### 5.1 Files

| File | Change |
|------|--------|
| `app/services/booking/pipeline.py` | try/except wrapper; compensation calls |
| `app/services/booking/sheets_writer.py` | `delete_workout_row(workout_id)` best-effort |
| `app/services/booking/calendar_writer.py` | `delete_calendar_event(event_id)` best-effort |
| `tests/unit/test_booking_pipeline_phase2.py` | mock Client_Workouts fail → no orphan Workouts |

### 5.2 Logging

```python
logger.error(
    "booking_sheets_partial_failure",
    extra={
        "workout_id_tail": event_id[-8:],
        "workouts_written": True,
        "client_workouts_written": False,
        "compensation": "calendar_delete+workout_row_delete",
    },
)
```

No PII.

### 5.3 User-facing

HTTP 500 «Не удалось завершить запись» — same as Calendar fail today; user can retry (idempotency may catch dup if Calendar still exists — recheck handles).

---

## 6. Documented cleanup procedure (Option E — interim)

Until Option B shipped:

1. Find orphan: Workouts row with `workout_id=X` and no Client_Workouts referencing `X`.
2. Verify Calendar event `X` — cancel if test/erroneous booking.
3. Delete Workouts row (or mark inactive if column exists).
4. Log incident with date/time/service_type (no phone in ticket title).

**Query pattern (manual):** compare `Workouts.workout_id` set vs `Client_Workouts.workout_id` set for same date.

---

## 7. Test plan

| Test | Assert |
|------|--------|
| `test_client_workout_fail_deletes_workout_row` | Workouts not left orphan |
| `test_client_workout_fail_deletes_calendar_event` | Calendar compensated (mock) |
| `test_calendar_fail_still_no_sheets` | Regression PR3 |
| Staging fault injection | Manual checklist S-PS1 |

---

## 8. Definition of Done (follow-up)

- [ ] Owner selects option (default recommend: **B + E runbook**)
- [ ] GM approval for follow-up PR (not mixed with PR4 unless small)
- [ ] Unit tests green
- [ ] Staging fault test executed
- [ ] Runbook linked from merge package
- [ ] Gate: **done before prod flags ON** (recommended)

---

## 9. Estimate

| Option | Effort |
|--------|--------|
| B — compensation | 1–1.5 days |
| E — runbook only | 0.25 day |
| D — repair job | 2–3 days |

---

## 10. References

- PR16 risk acceptance: [`BOOKING_PHASE2_PR16_MERGE_PACKAGE.md`](BOOKING_PHASE2_PR16_MERGE_PACKAGE.md) §0.1, §9
- Pipeline: `app/services/booking/pipeline.py`
