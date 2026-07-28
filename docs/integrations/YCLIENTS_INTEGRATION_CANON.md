# YCLIENTS Integration Canon — MyWave Wake (boat only)

**Статус:** S5 contract ready (код), S5 live smoke — blocked on Owner credentials  
**Company ID:** `2043174`  
**Виджет:** https://n347190.yclients.com/company/2043174/personal/menu?o=  
**Webhook:** `https://mywavewake.ru/public/integrations/yclients/webhook?token=<SECRET>`

---

## 1. Что обнаружено

1. В Site уже был scaffold (flags OFF): provider, webhook stub, sync stub.
2. Ответ YCLIENTS (support / api@yclients.tech) закрыл блокеры S5–S6 по auth, endpoints, webhooks, multi-set, PII.
3. Канон продукта: **YCLIENTS = SoT только для катера**; GCal = зеркало; Sheets = журнал; gym остаётся Site/TGbotAdmin.

## 2. Почему это важно

Без единого адаптера Site и Telegram пишут в разные контуры → двойные записи и расхождение слотов.  
Ответ YCLIENTS фиксирует: `record_id` стабилен после переноса; источник канала — только `comment` / `custom_fields` / `api_id`.

## 3. Решение (канон)

| Слой | Роль |
|------|------|
| Site + TGbotAdmin | Product shell → **только** internal gateway |
| `YclientsProvider` | Единый adapter |
| YCLIENTS | Source of Truth (boat) |
| Google Calendar | Операционное зеркало (закрытый) |
| Sheets | Audit / журнал |
| Telegram | Команды + notify + approve UX |

### Auth

```
Accept: application/vnd.yclients.v2+json
Authorization: Bearer <PARTNER_TOKEN>, User <USER_TOKEN>
Base: https://api.yclients.com/api/v1/
```

- Partner token — ЛК разработчика → «Токен партнера».
- User token — вкладка приложения **или** `POST /auth` с login/password пользователя филиала.
- Приложение должно быть **подключено к филиалу** 2043174 (публичное через Marketplace или непубличное — по гайду support).
- Для запросов «через юзера» приложение создавать не обязательно, но partner token из ЛК разработчика нужен.

### Flags

| Flag | Prod default | Meaning |
|------|--------------|---------|
| `YCLIENTS_ENABLED` | `0` | Master switch |
| `YCLIENTS_READ_ONLY_ENABLED` | `1` (when master on) | S5 read |
| `YCLIENTS_WRITE_ENABLED` | `0` | S6 write |

### Endpoints (рекомендованные YCLIENTS)

| Задача | Method / path |
|--------|----------------|
| Компания | `GET /company/{id}/` |
| Сотрудники | `GET /staff/{company_id}` |
| Услуги | `GET /services/{company_id}` |
| Свободные слоты | `GET /book_times/{company_id}/{staff_id}/{date}` |
| Онлайн-создание | `POST /book_record/{company_id}` |
| Журнал-создание | `POST /records/{company_id}` |
| Список записей | `GET /records/{company_id}` |
| Одна запись | `GET /record/{company_id}/{record_id}` |
| Изменение / перенос | `PUT /record/{company_id}/{record_id}` |
| Отмена (статус) | `attendance: -1` |

### Multi-set (30 мин × N)

Рекомендация YCLIENTS: **одна запись увеличенной длительности**.  
У нас: journal create с `seance_length = N * 30 * 60`.

### Источник канала

Нативный «source» передать нельзя. Канон MyWave:

- `comment`: `mw_source=site|telegram|widget|admin | mw_id=<internal>`
- `api_id`: внутренний ID
- `custom_fields`: опционально (после создания полей в ЛК YCLIENTS)

### Webhook

- События record: `create` / `update` / `delete`
- Подписи нет → секрет в query `?token=`
- Retry нет → идемпотентная обработка + cron reconcile
- Любой HTTP-ответ считается доставкой

### Лимиты

- 200 req/min **или** 5 rps на partner token
- Токены бессрочные; ротация через support
- Тестовой среды нет → тестовая компания

### Сезонные правила катера

До 30.09.2026: Пн закрыт; Чт 16:00–20:00 закрыт — **через график сотрудника в YCLIENTS**; API слотов учитывает график + перерывы + существующие записи.

## 4. Файлы

- `app/config/yclients_config.py`
- `app/services/booking/providers/yclients.py`
- `app/services/booking/yclients_sync.py`
- `app/routes/integrations/yclients.py`
- `scripts/yclients_discover.py`
- `scripts/yclients_auth_user_token.py`
- `scripts/yclients_smoke_read.py`
- `scripts/sync_yclients_bookings.py`
- `docs/deploy/YCLIENTS_SERVER_COMMANDS.md`

## 5. Что переносим как есть

- Company ID `2043174`, widget URL, boat-only scope, seasonal schedule intent.

## 6. Что рефакторим

- Provider: реальные endpoints + Accept + `Bearer, User`
- Webhook: envelope `resource/status/data` + URL token
- Internal gateway для Site/Bot без прямого write в YCLIENTS из бота

## 7. Что откладываем

- Полный GCal mirror upsert (после S5 PASS)
- Включение `YCLIENTS_WRITE_ENABLED=1` на prod (S6 + Owner GO)
- Переключение публичной формы Site с виджета на gateway write
- Gym → YCLIENTS (никогда в текущем каноне)

## 8. Риски

| Риск | Митигация |
|------|-----------|
| Два writer’а Site+Bot | Только gateway |
| Дубль record | Идемпотентность по `record_id` + `api_id` |
| Нет retry webhook | Cron `sync_yclients_bookings.py` |
| Нет credentials | S5 blocked до Owner |
| PII в открытом API | Только закрытый GCal / internal |

## 9. Критерий готовности

- [ ] Partner + User token в `.env` (не в git)
- [ ] `yclients_discover.py` → STAFF_ID + SERVICE_IDS
- [ ] `yclients_smoke_read.py` → SMOKE PASS
- [ ] Webhook URL с token в ЛК YCLIENTS
- [ ] Flags: ENABLED=1, READ=1, WRITE=0 на staging/smoke
- [ ] Owner GO перед WRITE=1
