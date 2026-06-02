# BOOKING_CALENDAR_EVENT_CONTRACT_v2

**Версия:** 2.0 (approved — TGbotAdmin sign-off 2026-06-01)  
**Статус:** ✅ approved  
**Базовый контракт:** [`BOOKING_CALENDAR_EVENT_CONTRACT_v1.md`](BOOKING_CALENDAR_EVENT_CONTRACT_v1.md) — **не отменяется**  
**Scope:** Site Phase 2 — Зал/Катер, multi-set Катер, summary v2, gym location v2  
**SoT занятости:** Google Calendar (без изменений)  
**Production Phase 1:** green — v2 включается только через feature flags после approved rollout

**Changelog v1.1:** capacity rules — см. [`BOOKING_AVAILABILITY_CONTRACT_v1.md`](BOOKING_AVAILABILITY_CONTRACT_v1.md) §4.

---

## 0. Связь с v1.0

| Тема | v1.0 (Phase 1, production) | v2.0 (Phase 2) |
|------|------------------------------|----------------|
| Calendar-first | ✅ | ✅ без изменений |
| `workout_id = event.id` | ✅ | ✅ |
| Telegram summary `(ID: tg_id)` | ✅ | **не менять** |
| Web marker `(WEB_ID: booking_id)` | ✅ | ✅ |
| Summary web формат | `Тренировка (<Локация>) — …` | **новый шаблон §3** (flag) |
| Boat 1 сет | 1 event, 30 min | ✅ совместимо |
| Boat N сетов | **N events** (v1 §9) | **1 continuous event** (amendment §9) |
| Gym location | `Зал MyWave` | **`Зал` + coords/map §5** (flag) |
| Availability | Site Sheets slots (Phase 1) | Calendar interval engine (отдельный контракт) |

**Amendment v1 §9:** для Phase 2 multi-set Катер принимается **1 Calendar event на весь диапазон**, не N events.

---

## 1. Принцип (без изменений)

Site **не** создаёт booking в обход Calendar. Sheets — журнал **после** Calendar insert.

**Порядок операций:** Calendar → `event.id` → Clients → Workouts → Client_Workouts.

---

## 2. Форматы тренировки

| `service_type` | Отображение | Duration |
|----------------|-------------|----------|
| `gym` | Зал | **90 мин** (фикс.) |
| `boat` | Катер | **30 мин × N сетов** (N ≥ 1, смежные) |

---

## 3. Поле `summary`

### 3.1 Telegram — **без изменений (v1)**

```text
Тренировка (<Локация>) — <Имя> (ID: <telegram_user_id>)
```

`<Локация>`: `Зал` | `Катер`.

TGbotAdmin antid dup по `(ID: …)` **не трогаем**.

### 3.2 Web — **шаблон v2 (Site Phase 2)**

**Зал:**

```text
Тренировка — Зал — <Имя> (WEB_ID: <site_booking_id>)
```

**Катер (N сетов):**

```text
Тренировка — Катер — <N> <сет|сета|сетов> — <Имя> (WEB_ID: <site_booking_id>)
```

**Склонение N:**

| N | Фрагмент |
|---|----------|
| 1 | `1 сет` |
| 2, 3, 4 | `N сета` |
| 5–20, … | `N сетов` |

**Примеры:**

```text
Тренировка — Зал — Иван (WEB_ID: bk_a1b2c3d4)
Тренировка — Катер — 1 сет — Иван (WEB_ID: bk_a1b2c3d4)
Тренировка — Катер — 3 сета — Иван (WEB_ID: bk_a1b2c3d4)
```

### 3.3 Fallback Phase 1 (feature flag OFF)

При `BOOKING_PHASE2_SUMMARY_V2=0` Site продолжает писать summary по **v1 §3.2**:

```text
Тренировка (<Локация>) — <Имя> (WEB_ID: <booking_id>)
```

---

## 4. Поле `description`

Audit-only (v1). TGbotAdmin **не парсит**.

**Дополнительные поля Phase 2 (рекомендуется):**

```text
set_count: 3
duration_min: 90
start_time: 2026-06-03T15:00:00+03:00
end_time: 2026-06-03T16:30:00+03:00
```

---

## 5. Поле `location`

| `service_type` | Phase 1 (production) | Phase 2 (flag ON) |
|----------------|----------------------|-------------------|
| `boat` | `MyWave Wake — https://yandex.ru/maps/org/mywave_wake/90003306477/` | **без изменений** |
| `gym` | `Зал MyWave` | **`Зал`** |

**Gym confirmation / UX (Site, не обязательно в Calendar `location`):**

| Поле | Значение |
|------|----------|
| Координаты | `55.777052, 37.502594` |
| Карта | `https://yandex.ru/maps/-/CLWQy6-I` |

Координаты могут дублироваться в success-modal / schema.org; в Calendar event — опционально через `location` или audit `description`.

---

## 6. `start` / `end` / `timeZone`

| Параметр | Значение |
|----------|----------|
| `timeZone` | `Europe/Moscow` |

### 6.1 Duration

| `service_type` | `end − start` |
|----------------|---------------|
| `gym` | **90 min** |
| `boat`, N=1 | **30 min** |
| `boat`, N>1 | **N × 30 min** (continuous interval) |

`start` = время **первого** сета.  
`end` = `start + duration`.

### 6.2 Multi-set Катер (amendment v1 §9)

| N сетов | Calendar events | `workout_id` | Sheets `Workouts` rows |
|---------|-----------------|--------------|------------------------|
| 1 | 1 | 1 × `event.id` | 1 |
| N (смежные) | **1** (continuous) | 1 × `event.id` | **1** (`duration` = N×30) |

**Client_Workouts:** 1 строка на booking (как Phase 1).

---

## 7. `extendedProperties.private` (web)

Phase 1 поля **сохраняются**. Добавления Phase 2:

```json
{
  "booking_id": "bk_...",
  "client_id": "client_...",
  "source": "web",
  "service_type": "gym|boat",
  "phone_hash": "<sha256 prefix>",
  "set_count": "3",
  "duration_min": "90"
}
```

- Открытый phone **не** писать.
- `set_count` для boat; для gym = `"1"` или omit.

---

## 8. Identity markers

| Источник | Marker |
|----------|--------|
| Telegram | `(ID: <telegram_user_id>)` — **frozen** |
| Site web | `(WEB_ID: <site_booking_id>)` |

Site **не** использует `(ID: client_…)` для web.

---

## 9. API payload (Site web booking)

### 9.1 Зал (без изменений полей)

```json
{
  "service_type": "gym",
  "date": "2026-06-01",
  "time": "12:00",
  "name": "...",
  "phone": "+7..."
}
```

### 9.2 Катер — один или несколько сетов

```json
{
  "service_type": "boat",
  "date": "2026-06-03",
  "time": "15:00",
  "set_count": 3,
  "name": "...",
  "phone": "+7..."
}
```

| Поле | Обязательность | Default |
|------|----------------|---------|
| `set_count` | optional | `1` |
| `time` | required | start первого 30-min слота |

**Правило:** все N сетов — **смежные** 30-min слоты от `time`.

Backward compatibility: при `set_count=1` или flag OFF — поведение Phase 1.

---

## 10. Idempotency (расширение v1)

| Уровень | Ключ Phase 2 |
|---------|--------------|
| API | `phone` + `date` + `start_time` + `end_time` + `service_type` |
| Заявка | `booking_id` |
| Calendar | overlap check до insert |
| Event | `extendedProperties.private.booking_id` |

Повтор submit с тем же `booking_id` → no duplicate.

---

## 11. Примеры событий v2

**Web, зал (90 min):**

```yaml
summary: "Тренировка — Зал — Иван (WEB_ID: bk_a1b2c3d4)"
location: "Зал"
start: 2026-06-01T12:00:00+03:00
end:   2026-06-01T13:30:00+03:00
timeZone: Europe/Moscow
```

**Web, катер (3 сета, 90 min continuous):**

```yaml
summary: "Тренировка — Катер — 3 сета — Иван (WEB_ID: bk_x9y8z7)"
location: "MyWave Wake — https://yandex.ru/maps/org/mywave_wake/90003306477/"
start: 2026-06-03T15:00:00+03:00
end:   2026-06-03T16:30:00+03:00
extendedProperties.private: {"booking_id":"bk_x9y8z7","set_count":"3","duration_min":"90",...}
```

**Telegram, катер (1 сет) — v1 формат, без изменений:**

```yaml
summary: "Тренировка (Катер) — Клиент (ID: 123456789)"
```

---

## 12. Feature flags (см. sync plan §Phase 2)

v2 summary/location/multi-set **не** активны в production по умолчанию.

---

## 13. Definition of Done — Calendar v2 (фрагмент)

- [ ] Summary v2 для web gym/boat (при flag ON)
- [ ] Telegram summary v1 unchanged
- [ ] Multi-set boat = 1 continuous event
- [ ] Duration gym 90 / boat 30×N
- [ ] Gym location `Зал`; boat location v1
- [ ] `extendedProperties` + `set_count` для boat N>1
- [ ] Phase 1 regression: single-set boat + gym при flags OFF

---

## 14. Sign-off (2026-06-01)

TGbotAdmin подтвердил: §9 (1 continuous event), §3.2 (summary v2), §5 (locations), travel buffer 120 min, WEB_ID, Calendar availability.

**Open (non-blocking, implementation):**

1. TGbotAdmin: парсить `set_count` из summary или только interval — prefer `extendedProperties`
2. Sheets `duration` column — map `duration` vs `duration_min` on prod (Phase 1 discovery)
