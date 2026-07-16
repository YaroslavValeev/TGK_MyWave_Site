# YCLIENTS Booking Gateway — совместный план Site + TGAdminBot

**Статус:** draft для согласования (read-only audit → gateway → write → reconcile)  
**Дата:** 2026-07-16  
**Владелец документа:** команда Site (Booking Gateway)  
**Потребители:** Site, TGAdminBot, Owner  
**Timezone:** `Europe/Moscow`

Связанные документы:

- [`TGBOT_SITE_BOOKING_SYNC_PLAN.md`](TGBOT_SITE_BOOKING_SYNC_PLAN.md) — текущий Calendar-first flow Phase 1/2
- [`BOOKING_AVAILABILITY_CONTRACT_v1.md`](BOOKING_AVAILABILITY_CONTRACT_v1.md)
- [`BOOKING_CALENDAR_EVENT_CONTRACT_v2.md`](BOOKING_CALENDAR_EVENT_CONTRACT_v2.md)
- [`BOOKING_ROW_CONTRACT_v1.md`](BOOKING_ROW_CONTRACT_v1.md)
- [`BOOKING_PHASE2_TGBOTADMIN_S7_HANDOFF.md`](BOOKING_PHASE2_TGBOTADMIN_S7_HANDOFF.md)
- [`../deploy/RELEASE_S4_YCLIENTS_BOAT_SCAFFOLD.md`](../deploy/RELEASE_S4_YCLIENTS_BOAT_SCAFFOLD.md)

---

## 1. Цель

Объединить запись на **катер MyWave / Руза** из всех источников:

- YCLIENTS (widget, ручная запись администратора);
- сайт MyWave;
- TGAdminBot.

Все источники показывают **одно актуальное расписание**. Создание, перенос и отмена синхронно отражаются в:

- YCLIENTS (источник истины для катера);
- Google Calendar (зеркало);
- Google Sheets (журнал);
- UI Site и TGAdminBot (через Booking Gateway).

**Зал MyWave** в scope YCLIENTS **не входит** (остаётся Calendar-first до отдельного решения).

---

## 2. Источник истины

| Сущность | SoT | Назначение |
|----------|-----|------------|
| Катер / Руза | **YCLIENTS** | расписание, доступность, статус записи |
| Зал MyWave | **Google Calendar** (как сейчас) | до 2026-09-30 сезонные ограничения в Site |
| Booking Gateway | Site | единая точка create/cancel/reschedule/read для boat |
| Google Calendar | зеркало | рабочий календарь, напоминания, ФИО в title |
| Google Sheets | журнал | операционная таблица, аналитика |
| Site / TGAdminBot | клиенты | **не** пишут напрямую в YCLIENTS |

---

## 3. Запрещённая схема

```text
TGAdminBot → YCLIENTS   ❌
Site       → YCLIENTS   ❌
```

Прямые интеграции дублируют: auth, маппинг услуг, слоты, ошибки, дедуп, cancel/reschedule, sync Calendar/Sheets.

**Канон:**

```text
TGAdminBot ───────┐
Site ─────────────┼──► Booking Gateway (Site)
Admin UI ─────────┘         │
                            ▼
                         YCLIENTS
                            │
                    external_booking_id
                            │
             ┌──────────────┴──────────────┐
             ▼                             ▼
      Google Calendar                Google Sheets
```

---

## 4. Текущее состояние Site (as-is)

| Компонент | Статус |
|-----------|--------|
| `POST /api/calendar/book` | production, Calendar-first |
| `execute_web_booking()` | Calendar → Sheets |
| YCLIENTS provider scaffold | `app/services/booking/providers/yclients.py`, **flags OFF** |
| Webhook stub | `/public/integrations/yclients/webhook` |
| `BOAT_PROVIDER` routing | **не реализован** (только env.example) |
| Boat slots | Calendar reader + Phase 2 flags |
| Ruza **camp** (`service_type=camp`) | отдельная ветка в `calendar_routes.py`, **не boat** |

**Вывод:** миграция boat = новый Gateway layer + переключение pipeline, не переписывание gym/camp с нуля.

---

## 5. Бизнес-правила

### 5.1 Катер MyWave / Руза

- один катер, один сотрудник, один клиент на слот;
- длительность слота: **30 минут**;
- `BOAT_CAPACITY=1`, `BOAT_SLOT_DURATION_MINUTES=30`.

### 5.2 Сезонные ограничения катера (до **2026-09-30** включительно)

Настраиваются **в YCLIENTS**; Gateway **дублирует проверку** server-side:

- понедельник — запись закрыта весь день;
- четверг — запись закрыта **16:00–20:00**.

### 5.3 Зал MyWave (без YCLIENTS)

- SoT: Google Calendar;
- до 2026-09-30: запись только **пн вечер** и **чт вечер** (`GYM_SEASONAL_WEEKDAYS=0,3`, `GYM_SEASONAL_START_TIME=19:00`);
- capacity: **4** (`GYM_CAPACITY=4`);
- с **2026-10-01** сезонное ограничение отключается конфигом (`BOOKING_SEASONAL_RULES_UNTIL`).

### 5.4 Google Calendar — отображение ФИО (катер)

Title:

```text
Катер / Руза — Имя Фамилия
```

Fallback: `Катер / Руза — Имя` → `Катер / Руза — Клиент`

Description (audit):

```text
Услуга:
Клиент:
Телефон:
Источник:
Статус:
YCLIENTS record ID:
MyWave booking ID:
```

**ФИО и телефон не отдаются в публичном availability API.**

---

## 6. Этап 0 — read-only audit (обязателен до write)

**Никаких POST create/cancel/reschedule на production.**

Зафиксировать в `docs/integration/YCLIENTS_READ_ONLY_AUDIT.md`:

| # | Данные |
|---|--------|
| 1 | `company_id`, `staff_id`, `service_id` |
| 2 | список услуг и сотрудников |
| 3 | расписание, доступные даты/интервалы |
| 4 | существующие записи, статусы, структура record ID |
| 5 | timezone |
| 6 | схема cancel / reschedule |
| 7 | webhooks, rate limits, auth |
| 8 | как отличать source: site / telegram / widget / admin |

**PR 1 deliverables:** реальные ID, примеры ответов **без PII**, audit-doc, flags read-only.

---

## 7. Booking Gateway API (целевой контракт)

Базовый префикс: `/api/v1/booking`

| Method | Path | Назначение |
|--------|------|------------|
| GET | `/availability` | слоты (без PII) |
| GET | `/bookings/{id}` | каноническая запись |
| POST | `/bookings` | создание |
| POST | `/bookings/{id}/cancel` | отмена |
| POST | `/bookings/{id}/reschedule` | перенос |

### 7.1 Request (create)

```json
{
  "service_type": "boat",
  "location_code": "ruza",
  "source_channel": "site",
  "client": {
    "first_name": "",
    "last_name": "",
    "phone": "",
    "telegram_user_id": ""
  },
  "start_at": "2026-07-20T10:00:00+03:00",
  "duration_minutes": 30,
  "idempotency_key": "site:booking_request_uuid"
}
```

`source_channel`: `site` | `telegram` | `admin`

### 7.2 Response (canonical booking)

```json
{
  "booking_id": "mw_...",
  "external_booking_id": "12345",
  "provider": "yclients",
  "status": "confirmed",
  "start_at": "",
  "end_at": "",
  "source_channel": "site"
}
```

### 7.3 Коды ошибок (единые для Site и TGAdminBot)

```text
slot_unavailable
seasonal_schedule_restricted
provider_unavailable
provider_auth_error
booking_not_found
booking_already_cancelled
reschedule_not_available
invalid_service
invalid_client_data
duplicate_request
sync_pending
```

---

## 8. Порядок создания записи (boat, write phase)

```text
1. Site или TGAdminBot → Booking Gateway
2. Gateway: сезонные ограничения (server-side)
3. Gateway: повторная проверка слота в YCLIENTS
4. Gateway: create в YCLIENTS → external_booking_id
5. Успех YCLIENTS → mirror Google Calendar
6. Успех Calendar → строки Google Sheets
7. Ответ клиенту

Если YCLIENTS fail:
  - Calendar не создаётся
  - Sheets не пишутся
  - понятная ошибка клиенту
  - безопасный retry с тем же idempotency_key
```

---

## 9. Дедупликация и registry

**Внешний ключ:**

```text
yclients:{company_id}:{external_booking_id}
```

**Idempotency (обязателен):**

| Канал | Формат |
|-------|--------|
| Telegram | `telegram:{telegram_user_id}:{service}:{start_at}` |
| Site | `site:{booking_request_id}` |

Повтор с тем же ключом **не создаёт** вторую запись.

**source_channel** в registry: `site` | `telegram` | `yclients_widget` | `yclients_admin`

Metadata в YCLIENTS (если API позволяет):

```text
source=mywave_site | source=mywave_telegram
mywave_booking_id=...
```

---

## 10. План PR (Site repo)

| PR | Содержание | Production impact |
|----|------------|-------------------|
| **PR 1** | YCLIENTS read-only client + audit doc | flags OFF, no booking change |
| **PR 2** | Booking Gateway routes + registry; write OFF | availability via gateway optional |
| **PR 3** | YCLIENTS write behind `YCLIENTS_WRITE_ENABLED` | staging only |
| **PR 4** | Webhook + reconcile job | staging → prod after smoke |

### PR 1 — read-only client

Методы:

```text
get_company()
get_staff()
get_services()
get_schedule()
get_available_dates()
get_available_times()
get_records()
get_record()
```

Код: расширить `app/services/booking/providers/yclients.py`, скрипт audit `scripts/yclients_read_only_audit.py`.

### PR 2 — Gateway

- `app/routes/booking_gateway.py` (или `app/routes/api/v1/booking.py`)
- `app/services/booking/gateway/` — orchestration, seasonal rules, error mapping
- Site boat UI → gateway availability (feature flag)
- Legacy `/api/calendar/book` для boat **не удалять** до cutover

### PR 3 — write

- create/cancel/reschedule в YCLIENTS
- порядок YCLIENTS → Calendar → Sheets
- idempotency store (SQLite или Sheets column)

### PR 4 — reconcile

- webhook handler (реализовать `yclients_sync.py`)
- cron `scripts/sync_yclients_bookings.py`
- отчёт расхождений, восстановление mirror

---

## 11. Ответственность команд

### Site

- Booking Gateway, публичное API, YCLIENTS client/sync
- Calendar/Sheets mirror, registry, webhook, reconcile
- серверные сезонные ограничения boat + gym (gym без YCLIENTS)

### TGAdminBot

- boat flow **только через Gateway**
- `source_channel=telegram`, `telegram_user_id`, `idempotency_key`
- слоты только из gateway; cancel/reschedule только через gateway
- отказ от прямой записи катера в Calendar/Sheets после cutover

### Совместно

- единый payload, статусы, коды ошибок
- staging smoke (см. §13)
- production rollout по флагам

---

## 12. Feature flags

```env
BOOKING_GATEWAY_ENABLED=0

YCLIENTS_ENABLED=0
YCLIENTS_READ_ENABLED=0
YCLIENTS_WRITE_ENABLED=0
YCLIENTS_WEBHOOK_ENABLED=0
YCLIENTS_RECONCILE_ENABLED=0

BOOKING_SEASONAL_RULES_ENABLED=1
BOOKING_SEASONAL_RULES_UNTIL=2026-09-30

GYM_SEASONAL_WEEKDAYS=0,3
GYM_SEASONAL_START_TIME=19:00
GYM_CAPACITY=4

BOAT_CAPACITY=1
BOAT_SLOT_DURATION_MINUTES=30
```

Существующие Phase 2 flags (`BOOKING_PHASE2_*`) для gym/boat availability **сохраняются** до cutover boat на gateway.

---

## 13. Порядок миграции

1. Согласовать этот документ + read-only контракт.
2. PR 1: audit, реальные ID, примеры API.
3. PR 2: Gateway, write OFF; Site + TGAdminBot на **availability** gateway (staging).
4. PR 3: write ON staging; smoke create/cancel/reschedule.
5. Проверить Calendar mirror + Sheets + ФИО в title.
6. PR 4: webhook + reconcile на staging.
7. Production: Site boat write через gateway.
8. Production: TGAdminBot cutover.
9. Отключить Calendar-first **только для boat** (`service_type=boat`).
10. **Зал не затрагивать.**

---

## 14. Staging smoke (совместный)

1. Запись из Site.  
2. Запись из TGAdminBot.  
3. Ручная запись в YCLIENTS admin.  
4. Сверка YCLIENTS / Calendar / Sheets.  
5. Перенос в YCLIENTS.  
6. Отмена в YCLIENTS.  
7. Повтор webhook (idempotent).  
8. Симуляция недоступности YCLIENTS.  
9. Дубль-клик / повтор idempotency_key.  
10. Сезонное ограничение (пн катер, чт 16–20).

---

## 15. Rollback

| Уровень | Действие |
|---------|----------|
| Gateway | `BOOKING_GATEWAY_ENABLED=0` → legacy `/api/calendar/book` |
| YCLIENTS write | `YCLIENTS_WRITE_ENABLED=0` |
| Полный откат boat | `BOAT_PROVIDER=site` (Calendar-first), задокументировать в runbook |

Prod pin и SHA фиксировать в release notes перед каждым этапом.

---

## 16. Открытые вопросы (для audit)

- [ ] Точные `service_id` / `staff_id` для катера Руза в YCLIENTS
- [ ] Поддержка multi-set boat (несколько последовательных 30-min) в YCLIENTS
- [ ] Webhook events и подпись
- [ ] Поля comment/metadata для `source_channel`
- [ ] Rate limits и retry policy
- [ ] Staging credentials и отдельный `company_id` (если есть)

---

## 17. Критерий готовности этапа 0 (audit)

- [ ] Audit-doc заполнен без PII
- [ ] Owner подтвердил ID и timezone
- [ ] TGAdminBot подтвердил контракт gateway payload
- [ ] Нет production write в YCLIENTS
- [ ] Rollback path задокументирован

**Следующий шаг после согласования:** PR 1 (read-only client + audit script).
