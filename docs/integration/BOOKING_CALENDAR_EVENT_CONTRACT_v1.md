# BOOKING_CALENDAR_EVENT_CONTRACT_v1

**Версия:** 1.0 (закрыты TBD)  
**Статус:** ✅ утверждено для Phase 1 PR (Site + TGbotAdmin, 2026-05-27)  
**SoT занятости:** Google Calendar  
**Журнал:** Sheets `Clients`, `Workouts`, `Client_Workouts`  
**Источник TGbotAdmin:** `bot/handlers.py`, `bot/utils.py`, `bot/main.py`

---

## 1. Принцип

Site **не** считает Sheets единственным источником занятости и **не** создаёт booking в обход Calendar.

| Слой | Роль |
|------|------|
| Google Calendar | занятость, слоты, подтверждённое событие |
| Sheets | журнал **после** успешного Calendar insert |

---

## 2. Порядок операций (канон Phase 1)

```
1. Calendar events().insert
2. event.id
3. workout_id = event.id
4. Clients find/create
5. Workouts
6. Client_Workouts
```

`calendar_event_id` как отдельная колонка в Sheets **не обязательна** (`workout_id` = `event.id`).

---

## 3. Поле `summary`

### 3.1 Telegram-клиент (совместимость с TGbotAdmin)

**Шаблон:**

```text
Тренировка (<Локация>) — <Имя> (ID: <telegram_user_id>)
```

**Примеры:**

```text
Тренировка (Зал) — Клиент_1 (ID: 123456789)
Тренировка (Катер) — Клиент_2 (ID: 987654321)
```

**Парсинг ботом:** поиск **подстроки** `(ID: <...>)` (regex/split нет).

**Дедуп TGbotAdmin:** если в событиях **того же интервала** уже есть `(ID: <тот же telegram_user_id>)` → «Вы уже записаны на этот слот».

**Маппинг `<Локация>`:**

| `service_type` | `<Локация>` |
|----------------|-------------|
| `gym` | `Зал` |
| `boat` | `Катер` |

### 3.2 Web-клиент (без Telegram ID) — **решение Phase 1**

| Вариант | Статус |
|---------|--------|
| A `(WEB_ID: …)` в summary | ✅ **принят** для web |
| B `(ID: client_…)` в summary | ❌ не использовать без отдельного PR TGbotAdmin (риск путаницы с Telegram ID) |

**Шаблон web:**

```text
Тренировка (<Локация>) — <Имя> (WEB_ID: <booking_id>)
```

**Пример:**

```text
Тренировка (Катер) — Иван (WEB_ID: bk_a1b2c3d4)
```

- `booking_id` — UUID/idempotency key одной заявки (один сет или пачка сетов).
- TGbotAdmin **сейчас не** использует `WEB_ID` для дедупа → **idempotency на Site** (§7).

**Site as-is (исправить в Phase 1):** `Тренировка: {name}` без локации и маркера.

---

## 4. Поле `description`

TGbotAdmin **не парсит** `description` для записи/дедупа. Писать **можно** (audit / будущий PR бота), но **не** считать частью активной логики бота.

**Рекомендуемый key-value (Site):**

```text
phone: +79160117179
telegram_id:
client_id: client_173...
workout_id: <calendar_event_id>
source: web
service_type: boat
booking_id: bk_a1b2c3d4
```

---

## 5. Поле `location`

| `service_type` | Значение (константа) |
|----------------|----------------------|
| `boat` | `MyWave Wake — https://yandex.ru/maps/org/mywave_wake/90003306477/` |
| `gym` | `Зал MyWave` (константа; уточнить адрес у Owner — **не** свободный текст) |

Координаты `55.759809`, `36.263791` — только UX/schema (`app/config/venue.py`).

---

## 6. `start` / `end` / `timeZone`

| Параметр | Значение |
|----------|----------|
| `timeZone` | `Europe/Moscow` |

### 6.1 Канон Owner (Site `calendar_writer`)

| `service_type` | `end − start` | Примечание |
|----------------|---------------|------------|
| `gym` | **90 мин** | одно занятие в зале |
| `boat` | **30 мин** | один **сет** (25 мин катание + 5 мин тех.) |

Константы: `app/config/booking_durations.py`.

### 6.2 TGbotAdmin (текущий флоу)

Сейчас бот часто использует **`end = start + 60 min`** для всех типов.

| Действие | Owner |
|----------|-------|
| Phase 1 Site | пишет Calendar по **§6.1** |
| Joint follow-up | выровнять сетку слотов и capacity бота под 90 / 30 |

⚠️ Не смешивать: зал ≠ 30 мин, катер ≠ 90 мин на один сет.

---

## 7. `extendedProperties.private` (web idempotency)

TGbotAdmin **не использует** сейчас — Site **может** писать без поломки бота.

**Канон Phase 1 (web):**

```json
{
  "booking_id": "bk_...",
  "client_id": "client_...",
  "source": "web",
  "service_type": "boat",
  "phone_hash": "<sha256 tail, не полный phone в логах>"
}
```

Дополнительно к `WEB_ID` в summary и API-дедупу (§8).

---

## 8. Дедуп

### 8.1 TGbotAdmin

1. Вместимость: `count(events in interval) < MAX_CAPACITY`
2. Клиент: подстрока `(ID: telegram_user_id)` в `summary` **того же интервала**

### 8.2 Site (web, обязательно)

| Уровень | Ключ |
|---------|------|
| API | `phone` + `date` + `time` + `service_type` |
| Заявка | `booking_id` (повтор submit) |
| Calendar | интервал слота + проверка занятости до insert |
| Event | `extendedProperties.private.booking_id` (где поддерживается) |

**WEB_ID** в summary **не** заменяет дедуп TGbotAdmin — только Site.

### 8.3 Telegram-записи

Формат `(ID: telegram_user_id)` **не менять** — полная совместимость с антидублем бота.

---

## 9. Катер: несколько сетов (Owner + Phase 1 API)

| Правило | Значение |
|---------|----------|
| 1 сет | 30 мин, 1 Calendar event, 1 `workout_id` |
| N сетов | **N events**, N `workout_id` (не один event на N×30 мин) |
| Заявка | `booking_id` общий; `slots: [{date, time}, …]` в API |
| UI | Phase 1.5 (мультивыбор); Phase 1 — заложить API |

---

## 10. Примеры событий

**Telegram, зал (90 мин):**

```yaml
summary: "Тренировка (Зал) — Клиент_1 (ID: 123456789)"
start: 2026-06-01T12:00:00+03:00
end:   2026-06-01T13:30:00+03:00
timeZone: Europe/Moscow
```

**Web, катер (30 мин, 1 сет):**

```yaml
summary: "Тренировка (Катер) — Иван (WEB_ID: bk_a1b2c3d4)"
location: "MyWave Wake — https://yandex.ru/maps/org/mywave_wake/90003306477/"
start: 2026-06-03T15:00:00+03:00
end:   2026-06-03T15:30:00+03:00
extendedProperties.private: {"booking_id":"bk_a1b2c3d4","source":"web",...}
```

---

## 11. Phase 1 — что не делать

- `send_telegram_notification()` в `calendar_routes.py`
- Запись в Sheets без Calendar
- Web summary с `(ID: client_…)` без согласования TGbotAdmin
- Считать `description` частью логики бота

---

## 12. Definition of Done (фрагмент)

См. полный DoD в `TGBOT_SITE_BOOKING_SYNC_PLAN.md` §10.

- [ ] Calendar insert → `workout_id = event.id`
- [ ] Summary: Telegram `(ID: tg_id)` / web `(WEB_ID: booking_id)`
- [ ] Длительности §6.1
- [ ] Web idempotency §8.2
