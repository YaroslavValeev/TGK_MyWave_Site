# Runbook: orphan Workouts без пары в Client_Workouts

**Версия:** 1.0
**Дата:** 2026-06-05
**Статус:** Option E (ops) + Option B (code compensation in pipeline)
**Связано:** [`BOOKING_PARTIAL_SHEETS_FOLLOWUP.md`](../integration/BOOKING_PARTIAL_SHEETS_FOLLOWUP.md)

---

## 1. Когда применять

| Ситуация | Действие |
|----------|----------|
| После deploy **Option B** (compensation PR) | Orphan **не должны** появляться при partial failure; runbook — для legacy/incident |
| Лог `booking_sheets_partial_failure` | Проверить compensation flags; при `workout_row_mark_failed` — ручная очистка |
| Ручной аудит перед staging E2E / flags ON | Профилактическая проверка |

**Не логировать в тикетах:** телефоны, полные `client_id` — только `workout_id` tail, date, time, service_type.

---

## 2. Определение orphan

**Orphan Workouts row:** строка в листе `Workouts`, где:

- `workout_id` = Google Calendar `event.id` (или legacy id);
- **нет** строки в `Client_Workouts` с тем же `workout_id`;
- `workout_status` ≠ `cancelled` (если колонка есть).

---

## 3. Поиск orphan (prod / staging)

### 3.1 Python на сервере (рекомендуется)

```bash
cd /var/www/mywave
source venv/bin/activate
export SECRET_KEY="${SECRET_KEY:-$(grep -E '^SECRET_KEY=' .env | cut -d= -f2-)}"

python - <<'PY'
from app import create_app
from app.services.google_sheets_service import read_records

app = create_app()
with app.app_context():
    sid = app.config["SPREADSHEET_ID"]
    workouts = read_records(sid, "Workouts")
    cw = read_records(sid, "Client_Workouts")
    cw_ids = {str(r.get("workout_id") or "") for r in cw if r.get("workout_id")}
    orphans = []
    for w in workouts:
        wid = str(w.get("workout_id") or "")
        if not wid:
            continue
        status = (w.get("workout_status") or "").strip().lower()
        if status == "cancelled":
            continue
        if wid not in cw_ids:
            orphans.append({
                "workout_id_tail": wid[-8:],
                "date": w.get("date"),
                "time": w.get("time"),
                "workout_type": w.get("workout_type"),
                "workout_status": status,
            })
    print("orphan_count", len(orphans))
    for o in orphans[:20]:
        print(o)
PY
```

**Ожидание после Option B:** `orphan_count 0` для новых booking после deploy compensation.

### 3.2 Ручно в Google Sheets

1. Открыть лист `Workouts`, скопировать колонку `workout_id` (активные строки).
2. Открыть `Client_Workouts`, колонка `workout_id`.
3. Найти `workout_id`, присутствующие в Workouts, но отсутствующие в Client_Workouts.

---

## 4. Проверка Calendar

Для каждого orphan `workout_id`:

1. Google Calendar (prod calendar id из `.env` `GOOGLE_CALENDAR_ID`).
2. Поиск события по id / по date+time из Workouts row.
3. Если booking ошибочный / тестовый — **удалить событие** в Calendar UI или через API.

---

## 5. Безопасное исправление

| Шаг | Действие |
|-----|----------|
| 1 | Подтвердить orphan (§3) |
| 2 | Проверить Calendar (§4) |
| 3 | **Предпочтительно:** в Workouts установить `workout_status` = `cancelled`, `current_capacity` = `0` |
| 4 | Альтернатива: удалить строку Workouts (только если Owner подтвердил и Calendar уже чист) |
| 5 | Записать incident (§6) |

**Не удалять** строки Client_Workouts без проверки — риск потери клиентской записи.

---

## 6. Incident report (шаблон)

```text
Incident: orphan Workouts
Date discovered: YYYY-MM-DD
Environment: production | staging
workout_id_tail: xxxxxxxx
Workouts date/time: YYYY-MM-DD HH:MM
service_type: gym | boat
Calendar event: present | deleted | n/a
Action taken: marked cancelled | row deleted | calendar deleted
Compensation log: booking_sheets_partial_failure (yes/no)
Follow-up: none | staging fault test | code fix
```

---

## 7. Автоматическая compensation (Option B — code)

При `write_workout_row()` OK + `write_client_workout_row()` FAIL pipeline:

1. `compensate_workout_row(workout_id)` → `workout_status=cancelled`
2. `delete_calendar_event_best_effort(workout_id)`
3. Log: `booking_sheets_partial_failure`
4. HTTP 500 пользователю: «Не удалось завершить запись»

См. `app/services/booking/pipeline.py` → `_compensate_partial_sheets_failure`.

**Regression suite (PR #18):** `87 passed` — booking suite + 6 compensation tests (`test_booking_sheets_compensation.py`).

---

## 8. Rollback / disable

Compensation активна **без feature flags** (всегда при partial failure).
Rollback: revert compensation PR на `main` + redeploy `mywave-site` only.

---

## 9. Контакты

- **Site:** pipeline / sheets_writer
- **Owner:** approve row delete (не mark)
- **TGbotAdmin:** inform if Calendar contract affected
