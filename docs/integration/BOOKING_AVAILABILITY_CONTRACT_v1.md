# BOOKING_AVAILABILITY_CONTRACT_v1

**Версия:** 1.1 (amendment — capacity rules, Site + TGbotAdmin 2026-06-01)  
**Статус:** ✅ approved  
**Scope:** Site Phase 2 availability engine  
**SoT занятости:** Google Calendar (primary)  
**Связанные контракты:** [`BOOKING_CALENDAR_EVENT_CONTRACT_v2.md`](BOOKING_CALENDAR_EVENT_CONTRACT_v2.md)

**Changelog v1.1:** зафиксированы capacity rules — Катер exclusive interval; Зал group capacity до 4 клиентов на 90-min slot.

---

## 1. Цель

Единая проверка доступности слотов для Site web booking:

- **Катер:** interval conflict (exclusive, 1 клиент на boat-slot);
- **Зал:** capacity-based logic (до **4** клиентов на 90-min slot);
- gym 90 min / boat 30 min × N смежных сетов;
- travel buffer **2 часа** между Зал ↔ Катер;
- скрытие недоступных слотов/диапазонов в UI;
- повторная проверка непосредственно перед подтверждением записи.

Phase 1 (Sheets-based slot counting) остаётся **fallback** при `BOOKING_PHASE2_AVAILABILITY=0`.

---

## 2. Источники данных

| Источник | Роль Phase 2 | Роль Phase 1 (fallback) |
|----------|--------------|-------------------------|
| Google Calendar | **primary** — confirmed events дня | не используется для slots API |
| Sheets `Client_Workouts` | secondary / audit | primary для boat/gym slots |
| Sheets `Schedule` | gym slot grid (start times) | primary для gym |

**Канон Phase 2:** занятость считается по **Calendar events** за запрашиваемый день (+ buffer window §6).  
Для **Зала** дополнительно применяется group capacity §4.2 (не pure binary overlap).

---

## 3. Константы capacity

| Константа | Значение | Применение |
|-----------|----------|------------|
| `BOAT_SET_MINUTES` | **30** | один сет катера |
| `BOAT_MAX_CLIENTS_PER_SLOT` | **1** | exclusive: один клиент на boat-slot |
| `GYM_SLOT_MINUTES` | **90** | длительность gym-slot |
| `GYM_MAX_CLIENTS_PER_SLOT` | **4** | group: до 4 клиентов на gym-slot |
| `TRAINER_TRAVEL_BUFFER_MINUTES` | **120** | buffer Зал ↔ Катер (§6) |

---

## 4. Capacity rules (business)

### 4.1 Катер — exclusive interval

| Правило | Описание |
|---------|----------|
| Длительность сета | **30 минут** |
| Вместимость | **1 клиент** на boat-slot |
| Несколько клиентов | **недопустимы** в одном boat-slot |
| Multi-set | N смежных сетов = **1 continuous interval**; блокирует весь диапазон для других клиентов |
| Проверка | **interval conflict** = полный блокер (любой overlap → slot недоступен) |

**Пример:**

```text
Клиент A занял катер 18:00–19:00 (4 сета).
→ Сеты 18:00 и 18:30 недоступны для других клиентов.
→ Любой candidate boat interval, пересекающий [18:00, 19:00), blocked.
```

**Overlap (канон для катера):**

```text
overlap(A, B) ⇔ A.start < B.end AND B.start < A.end
```

Candidate boat `[T, T+N×30)` **недоступен**, если overlap с **любым** существующим boat-event (Telegram + web).

### 4.2 Зал — group capacity

| Правило | Описание |
|---------|----------|
| Длительность slot | **90 минут** |
| Вместимость | **до 4 клиентов** на один gym-slot |
| Доступность | slot доступен, пока `occupancy < 4` |
| Блокировка | slot недоступен при **4/4** |
| Проверка | **capacity-based**, не binary overlap |

**Gym-slot** задаётся якорем `(date, start_time T)` из Schedule; candidate interval = `[T, T+90min)`.

**Occupancy (Phase 2, Calendar SoT):**

```text
occupancy(gym_slot[T]) = count(
  Calendar events e
  WHERE e.service_type == gym
    AND overlap([T, T+90min), e.interval)
    AND e.status != cancelled
)
```

```text
remaining = GYM_MAX_CLIENTS_PER_SLOT - occupancy
available ⇔ remaining > 0
```

**Важно:** несколько gym-events с **одинаковым** `[T, T+90)` — нормальный сценарий (group class).  
Первый overlap **не** блокирует slot; блокировка только при `occupancy >= 4`.

**Пример:**

```text
Gym-slot 10:00–11:30: уже 3 клиента (3 Calendar events).
→ remaining = 1, slot available.
4-й клиент → occupancy = 4 → slot unavailable (4/4).
```

### 4.3 Сводка: Катер vs Зал

| | Катер | Зал |
|---|-------|-----|
| Модель | **Exclusive interval** | **Group capacity** |
| Max клиентов | 1 | 4 |
| Первый overlap | блокирует | уменьшает `remaining` |
| Multi-client same window | ❌ | ✅ (до 4) |
| SoT | Calendar events | Calendar events |

---

## 5. Интервалы и длительности

| Тип | Candidate interval `[start, end)` |
|-----|-----------------------------------|
| Зал | `[T, T+90min)` |
| Катер, N=1 | `[T, T+30min)` |
| Катер, N>1 | `[T, T+N×30min)` — continuous, смежные 30-min шаги |

**Шаг сетки катера:** 30 минут (06:00–21:00 MSK).  
**Шаг сетки зала:** по Schedule (start time = якорь slot).

---

## 6. Travel buffer (Зал ↔ Катер)

| Константа | Значение |
|-----------|----------|
| `TRAINER_TRAVEL_BUFFER_MINUTES` | **120** (2 часа) |

### 6.1 Правило

Если на дате D есть подтверждённое событие типа **A**, candidate типа **B** (A≠B) **недоступен**, если:

```text
NOT (candidate.end + BUFFER <= existing.start
  OR candidate.start >= existing.end + BUFFER)
```

Тип события:

1. `extendedProperties.private.service_type`, или
2. парсинг summary (`Зал` / `Катер`), или
3. duration heuristic (fallback, не primary).

Buffer проверяется **после** capacity/overlap правил §4 и **до** финального allow.

### 6.2 Примеры

| Existing | Candidate | Result |
|----------|-----------|--------|
| Boat 12:00–12:30 | Gym 13:00–14:30 | ❌ blocked (buffer until 14:30) |
| Boat 12:00–12:30 | Gym 14:30–16:00 | ✅ allowed (if gym capacity OK) |
| Gym 10:00–11:30 (3/4) | Boat 13:30–14:00 | ✅ allowed |
| Gym 10:00–11:30 | Boat 12:00–12:30 | ❌ blocked (buffer) |

Buffer **симметричен** gym→boat и boat→gym.

---

## 7. Multi-set Катер

### 7.1 Выбор N смежных сетов

- `time` — start первого 30-min слота;
- `set_count` = N ≥ 1.

**Доступно**, если:

1. candidate interval `[T, T+N×30)` **не overlap** ни с одним boat-event (§4.1);
2. каждый 30-min сегмент внутри диапазона эквивалентно свободен (следствие п.1 для exclusive model);
3. диапазон проходит travel buffer §6;
4. диапазон в operating hours (06:00–21:00 MSK).

### 7.2 UI

- не показывать `set_count`, для которых диапазон не проходит §7.1;
- preview: `18:00–19:00 (4 сета)`.

---

## 8. API (Site)

### 8.1 GET slots

**Gym** (Phase 2, flag ON):

```json
{
  "time": "10:00",
  "available": true,
  "remaining": 2,
  "max_capacity": 4
}
```

- `remaining` = `4 - occupancy` (Calendar count §4.2)
- `available` = `remaining > 0`
- Форма ответа **совместима** с Phase 1 (`remaining`, `available`)

**Boat** (Phase 2, flag ON):

```json
{
  "time": "15:00",
  "available": true,
  "max_set_count": 3
}
```

- `available` = false, если **любой** overlap с boat-event на `[time, time+30)` (или нет места для N≥1)
- `max_set_count` — max N смежных сетов от `time` (при `BOOKING_PHASE2_MULTI_SET_BOAT=1`)

### 8.2 POST book — pre-confirm recheck

Перед `events().insert` pipeline **обязан** повторно проверить:

- **Boat:** exclusive interval free;
- **Gym:** `occupancy < 4` для slot `[T, T+90)`.

При конфликте → `409` / «Слот уже занят» (boat) или «Нет мест в группе» (gym 4/4).

---

## 9. Порядок проверок (pipeline)

```text
1. Normalize phone, parse date/time/set_count
2. Build candidate interval [start, end)
3. Idempotency check
4. Availability check (Calendar):
   4a. Boat → exclusive overlap (§4.1)
   4b. Gym  → capacity count (§4.2)
   4c. Travel buffer (§6, if flag ON)
5. client_resolver
6. Calendar insert
7. Sheets write
```

Шаг 4 **пропускается** при `BOOKING_PHASE2_AVAILABILITY=0` (Phase 1 Sheets logic).

---

## 10. Что не показывать пользователю

- boat slots с overlap (exclusive);
- boat start times, где `max_set_count < 1`;
- gym slots с `remaining == 0` (4/4);
- gym slots, не проходящие 90-min window + buffer;
- прошедшее время (date = today).

---

## 11. Логирование (без PII)

| Event | Поля |
|-------|------|
| `availability_check` | `service_type`, `date`, `start`, `duration_min`, `set_count`, `available`, `remaining` (gym) |
| `availability_blocked_overlap` | `service_type`, `reason=exclusive` (boat) |
| `availability_blocked_capacity` | `service_type`, `occupancy`, `max_capacity` (gym) |
| `availability_blocked_travel_buffer` | `existing_type`, `candidate_type`, `gap_min` |
| `availability_recheck_failed` | `booking_id_tail`, `reason` |

Phone / name **не** логировать.

---

## 12. Feature flags

| Flag | Default | Effect |
|------|---------|--------|
| `BOOKING_PHASE2_AVAILABILITY` | **OFF** | Calendar engine (§4 boat/gym split) |
| `BOOKING_PHASE2_MULTI_SET_BOAT` | **OFF** | `max_set_count`, multi-set UI/API |
| `BOOKING_PHASE2_TRAVEL_BUFFER` | **OFF** | §6 buffer (requires AVAILABILITY) |

При всех OFF — Phase 1 Sheets slot logic без изменений.

---

## 13. Definition of Done — Availability v1.1

- [ ] Calendar read for day window
- [ ] **Boat:** exclusive interval conflict
- [ ] **Gym:** capacity count до 4 на 90-min slot
- [ ] Travel buffer 120 min gym↔boat
- [ ] Multi-set adjacent validation (boat)
- [ ] Pre-confirm recheck (boat exclusive + gym capacity)
- [ ] Fallback to Phase 1 when flag OFF
- [ ] Unit tests: boat overlap, gym 3/4→4/4, multi-set block, buffer
- [ ] Staging smoke with TGbotAdmin calendar

---

## 14. Совместимость с TGbotAdmin

TGbotAdmin должен использовать **те же** capacity rules:

- Катер: 1 клиент / interval, multi-set = continuous block;
- Зал: до 4 клиентов / 90-min slot;
- Travel buffer 120 min.

Site Phase 2 **не** меняет Telegram booking flow.

Joint smoke: web + bot не должны показывать conflicting availability на одном Calendar.

**Shared constants (documentation):**

```text
BOAT_MAX_CLIENTS_PER_SLOT=1
GYM_MAX_CLIENTS_PER_SLOT=4
TRAINER_TRAVEL_BUFFER_MINUTES=120
```
