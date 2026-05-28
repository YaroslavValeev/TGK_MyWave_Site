# BOOKING_ROW_CONTRACT_v1

**Версия:** 1.0 (закрыты TBD)  
**Статус:** ✅ утверждено для Phase 1 PR (2026-05-27)  
**Таблица:** `1kyNQVjeLLe4Ra6oWuf84fHqSjUlWXI8MakVMOrCgic0`  
**Предусловие:** успешный Calendar insert (`BOOKING_CALENDAR_EVENT_CONTRACT_v1.md`)

---

## 1. Порядок записи (канон)

```
1. Calendar event → event.id
2. workout_id = event.id
3. Clients find/create
4. Workouts
5. Client_Workouts
```

Sheets **не** создают занятость без события в Calendar.

---

## 2. Лист `Clients`

**Колонки TGbotAdmin:**

```text
client_id, telegram_user_id, name, phone, email, skill_level,
last_active, source, status, notes
```

| Поле | Telegram | Web (Site) |
|------|----------|------------|
| `client_id` | `str(telegram_user_id)` | reuse по phone или `client_<unix_ts>` / `web_<uuid>` |
| `telegram_user_id` | numeric | `""` (пусто) |
| `name` | из TG / формы | из формы |
| `phone` | если есть | `+7XXXXXXXXXX` |
| `source` | telegram | `web` |
| `status` | по боту | по resolver |
| остальные | опционально | опционально |

**Anti-overwrite:** если у найденного клиента есть `telegram_user_id` — **не затирать** пустым при web-записи.

---

## 3. Лист `Workouts`

**Колонки TGbotAdmin:**

```text
workout_id, date_time, duration_min, location, workout_type,
max_capacity, coach_name
```

| Поле | Канон Phase 1 |
|------|----------------|
| `workout_id` | **`event.id`** Google Calendar |
| `date_time` | ISO datetime начала (`Europe/Moscow`) |
| `duration_min` | **90** (`gym`) · **30** (`boat`, один сет) |
| `location` | константы из CALENDAR §5 |
| `workout_type` | `gym` / `boat` / … |
| `max_capacity` | из конфига слота |
| `coach_name` | опционально |

Отдельный столбец `calendar_event_id` — **не блокер** Phase 1 (дублирует `workout_id`).

**Site as-is:** поля `date`, `time`, `current_capacity` отдельно — **маппить** в writer по prod headers (discovery).

**N сетов катера:** N строк `Workouts` (по одному `workout_id` на сет).

---

## 4. Лист `Client_Workouts`

**Колонки TGbotAdmin:**

```text
client_workout_id, client_id, workout_id, payment_id, subscription_id,
booking_type, status, created_at
```

| Поле | Phase 1 Site |
|------|----------------|
| `client_workout_id` | `cw_<uuid>` (генерировать) |
| `client_id` | из resolver |
| `workout_id` | `event.id` |
| `payment_id` | пусто (web) |
| `subscription_id` | пусто |
| `booking_type` | `client` |
| `status` | **`подтверждено`** (см. §5) |
| `created_at` | ISO UTC |

Legacy поля Site (`date`, `time`, `service_type` отдельными колонками) — **не писать** вне согласованных заголовков prod; унифицировать через `sheets_writer`.

---

## 5. Статусы — **решение Phase 1**

| Слой | Значение |
|------|----------|
| Site internal (код/логи) | `booked` |
| **Sheets (запись)** | **`подтверждено`** |

**Обоснование:** минимальный риск совместимости с TGbotAdmin; слот уже в Calendar SoT.

**Маппинг в коде:**

```python
SHEETS_STATUS_CONFIRMED = "подтверждено"  # запись в Sheets
INTERNAL_STATUS_BOOKED = "booked"         # логи, API response
```

`pending` — **не** использовать после успешного Calendar insert.

---

## 6. Катер: несколько сетов

| 1 сет | N сетов |
|-------|---------|
| 1× Workouts + 1× Client_Workouts | N× каждого, общий `client_id`, общий `booking_id` в extendedProperties |

API Phase 1: `slots[]` в одном POST; UI мультивыбор — Phase 1.5.

---

## 7. Path A / Path B

| Путь | Вход | Phase 1 |
|------|------|---------|
| **A** | `POST /api/calendar/book` | `calendar_writer` → `sheets_writer` |
| **B** | `tools.py` / чат | **тот же pipeline**; **запрет** записи без Calendar |

---

## 8. Дедуп (Sheets)

| Правило | Когда |
|---------|-------|
| `(client_id, workout_id)` уникальны | одна связка на event |
| API: phone + date + time + service_type | до Calendar insert |
| `booking_id` | повторная отправка формы |

---

## 9. Discovery prod

Сверить заголовки листов скриптом в `TGBOT_SITE_BOOKING_SYNC_PLAN.md` §6 перед merge PR.

---

## 10. Definition of Done

- [ ] `workout_id` = `event.id` на каждый сет
- [ ] Порядок §1
- [ ] Path A/B — один writer
- [ ] Статус в Sheets: `подтверждено`
- [ ] Web: `telegram_user_id` пусто, `source=web`, без затирания TG id
