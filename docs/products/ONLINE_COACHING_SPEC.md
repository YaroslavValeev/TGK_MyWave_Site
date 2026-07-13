# MyWave Online Coaching — продуктовая спецификация (MVP)

## 1. Цель направления

Онлайн-услуги дополняют офлайн-тренировки: разбор видео, месячное сопровождение и Live Coach. Клиент понимает, что покупает; тренер получает заявки в Telegram; данные хранятся в Google Sheets; оплата — через Т-Банк (MVP: полуавтомат).

## 2. Матрица услуг

| service_type | Название | Цена MVP | payment_timing | Начальный статус заявки |
|---|---|---:|---|---|
| `video_check` | MyWave Video Check | 1 500 ₽ / сет | `after_service` | `waiting_video` / `video_received` |
| `progress_month` | MyWave Progress Month | 12 000 ₽ / месяц | `upfront` | `waiting_payment` |
| `live_coach_land` | Live Coach — суша | 3 500 ₽ (60 мин) | `after_service` | `new` |
| `live_coach_water` | Live Coach — вода | 3 500 ₽ (60 мин) | `after_service` | `new` |

**Live package (Phase 2):** `package_upfront` — не в MVP форме, только по запросу тренера.

## 3. Progress Month — лимиты MVP

- 30 календарных дней с даты оплаты
- До 10 тренировок в месяц
- До 3 роликов по 60–90 сек после каждой тренировки
- Срок ответа тренера: до 48 часов
- Доп. разборы сверх лимита — отдельная платная опция (вручную)

## 4. Каналы связи

| Канал | MVP |
|---|---|
| Telegram | Авто-уведомления тренеру |
| WhatsApp, MAX, телефон, email | Сохраняются в заявке, связь вручную |

## 5. Статусы заявки (state machine)

**Video Check:** `new` → `waiting_video` → `video_received` → `in_review` → `review_ready` → `review_sent` → `waiting_payment` → `paid` → `completed`

**Progress Month:** `new` → `waiting_payment` → `paid` → `subscription_active` → `waiting_next_video` → `video_received` → `in_review` → `diary_updated` → `renewal_offered` → `completed`

**Live:** `new` → `live_scheduled` → `live_completed` → `waiting_payment` → `paid` → `completed`

Общие: `waiting_contact`, `followup_scheduled`, `cancelled`

**Авто при submit:**
- `progress_month` → `waiting_payment`
- `video_check` без видео → `waiting_video`; с видео → `video_received`
- `live_coach_*` → `new`

## 6. Сценарии оплаты

### Video Check / разовый Live
1. Заявка → разбор/занятие → admin: `review_sent` / `live_completed`
2. Telegram: «Нужно отправить оплату»
3. Admin: ссылка Т-Банка → `link_sent` → «Оплачено» → `Sales_Deals`

### Progress Month
1. Заявка → `waiting_payment`
2. Admin: ссылка Т-Банка → оплата → `Subscriptions` (8 сессий, +30d)

## 7. Апсейл Video Check → Progress Month

После `review_sent` / `completed` тренер предлагает Progress Month:
- Admin: статус `renewal_offered`
- При согласии — новая заявка `progress_month`

## 8. Связь с офлайн

- `client_id` через `booking/client_resolver.py` (phone/name)
- Единая карточка в `Clients`
- Офлайн booking flow не меняется

## 9. Дневник (MVP)

Лист `Online_Diaries` + опциональная ссылка `diary_url` (Google Docs/Sheets). Запись через admin UI.

## 10. Видео (MVP)

- Ссылка в форме (Drive/Yandex/Telegram)
- Дублирование в `Media_Files`
- Загрузка на сервер — Phase 2

## 11. Отложено (Phase 2+)

- T-Bank API Init + webhook
- WhatsApp/MAX API
- Личный кабинет клиента
- GET `/api/online-coaching/status/<id>` (token-based)
- AI-оценка видео
- Автопродление подписки
