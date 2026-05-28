# Prod Sheets headers dump (2026-05-27)

**Spreadsheet:** `1kyNQVjeLLe4Ra6oWuf84fHqSjUlWXI8MakVMOrCgic0`  
**Script:** `scripts/dump_booking_sheets_headers.py`

## Clients (11 cols)

```text
client_id, telegram_user_id, name, phone, email, level, created_at, source, status, ref_code, last_active
```

## Client_Workouts (10 cols)

```text
id, client_id, workout_id, date, time, performance, feedback, payment_type, status, created_at
```

> Контракт v1.0 называет колонку `client_workout_id` — на prod фактически **`id`**. Writer Phase 1 пишет в `id`.

## Workouts (10 cols)

```text
workout_id, date, time, duration, location, workout_type, max_capacity, coach_name, workout_status, current_capacity
```

> Контракт TGbotAdmin также допускает `date_time` / `duration_min` — на prod раздельные `date`, `time`, `duration`. Writer маппит по prod headers.

## Schedule (3 cols)

```text
day_of_week, time, max_capacity
```
