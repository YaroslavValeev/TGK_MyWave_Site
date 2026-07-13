# MyWave Online Coaching — Pre-Build Report (Owner)

Дата: 2026-07-04. Статус: **подтверждено Owner → MVP в реализации**.

---

## 1. Финальная продуктовая матрица

| service_type | Продукт | Цена MVP | Оплата | Стартовый статус |
|---|---|---:|---|---|
| `video_check` | MyWave Video Check | 3 500 ₽ | после услуги | `waiting_video` / `video_received` |
| `progress_month` | Progress Month | 12 000 ₽/мес | upfront | `waiting_payment` |
| `live_coach_land` | Live Coach — суша | 3 500 ₽ | после занятия | `new` |
| `live_coach_water` | Live Coach — вода | 5 500 ₽ | после занятия | `new` |

Progress Month: 30 дней, до 8 тренировок, до 3 видео × 60–90 сек, ответ до 48 ч.

---

## 2. Финальные статусы

**Video Check:** `new` → `waiting_video` → `video_received` → `in_review` → `review_ready` → `review_sent` → `waiting_payment` → `paid` → `completed`

**Progress Month:** `new` → `waiting_payment` → `paid` → `subscription_active` → `waiting_next_video` → `video_received` → `in_review` → `diary_updated` → `renewal_offered` → `completed`

**Live:** `new` → `live_scheduled` → `live_completed` → `waiting_payment` → `paid` → `completed`

Общие: `waiting_contact`, `followup_scheduled`, `cancelled`

---

## 3. Финальная структура Sheets

**Переиспользуем:** `Clients`, `Subscriptions`, `Sales_Deals`, `Bot_Events`, `Media_Files` (если есть)

**Создаём MVP (идемпотентно):** `Online_Requests`, `Online_Diaries`, `Online_Payments`, `Online_Followups`

**Schema-only (не auto-create):** `Online_Reviews`

Скрипт: `scripts/ensure_online_coaching_sheets.py` — dry-run / APPLY, не трогает data rows.

---

## 4. Notification flow (Telegram)

| Событие | Триггер | Кнопки |
|---|---|---|
| Новая заявка | POST apply | Только «Открыть заявку» → admin |
| Видео получено | admin → `video_received` | «Открыть заявку» |
| Разбор готов | admin → `review_ready` | «Открыть заявку» |
| Разбор отправлен | admin → `review_sent` | «Открыть заявку» |
| Нужна оплата | admin → `waiting_payment` | «Открыть заявку» |
| Подписка активна | mark paid Progress Month | «Открыть заявку» |
| Сообщение клиента | Phase 2 / bot hook | «Открыть заявку» |

**Без PII в Telegram:** телефон маскируется, травмы → «указаны / не указаны», цель ≤60 символов. Полный текст — только admin UI.

**Запрещено:** GET-ссылки с `?action=...` для смены статуса.

---

## 5. Payment flow (T-Bank MVP)

1. **Progress Month:** заявка → `waiting_payment` → admin вставляет ссылку → `Online_Payments` → «Оплачено» → `Sales_Deals` + `Subscriptions` + `subscription_active`
2. **Video Check / Live разово:** разбор/занятие → `review_sent`/`live_completed` → `waiting_payment` → ссылка → «Оплачено» → `Sales_Deals`

Phase 2: T-Bank Init API + webhook.

---

## 6. Список файлов

| Слой | Файлы |
|---|---|
| Product | `docs/products/ONLINE_COACHING_SPEC.md`, этот report |
| Schema/Store | `app/services/online_coaching_{schema,store,payments,notifications,admin}.py` |
| Routes | `app/routes/online_coaching.py`, `app/routes/admin/online_coaching.py` |
| Config | `app/config/online_coaching_features.py`, `configs/services.yaml`, `env.example` |
| Frontend | `templates/services/online_coaching.html`, `static/css/online-coaching.css`, `static/js/online-coaching-form.js` |
| Admin UI | `templates/admin/online_coaching/{list,detail}.html` |
| Ops | `scripts/ensure_online_coaching_sheets.py`, `docs/deploy/ONLINE_COACHING_DEPLOY.md` |
| Tests | `tests/unit/test_online_coaching_*.py` (4 файла) |

---

## 7. MVP scope

Страница, форма, 4 service_type, Sheets, Telegram, admin UI, полуавтомат T-Bank, дневник, follow-up, Clients/Subscriptions/Sales_Deals/Media_Files/Bot_Events.

---

## 8. Out-of-scope (Phase 2+)

T-Bank API, WhatsApp/MAX auto, личный кабинет, upload видео на сервер, GET status API, TGbotAdmin changes, «Премиум сопровождение катального дня».

---

## 9. Риски

| Риск | Митигация |
|---|---|
| Sheets headers drift | Идемпотентный ensure script |
| PII в Telegram | sanitize_record_for_telegram |
| Случайная смена статуса по URL | Только admin POST |
| T-Bank credentials нет | Полуавтомат, не блокирует релиз |
| Регресс booking/social | Отдельный blueprint + feature flags |

---

## 10. План тестов

- Schema: enums, headers, initial status
- Store: append/update/diary/followup (mock Sheets)
- Payments: link + mark_paid + subscription
- Routes: page 200, apply 400/201, flag off → 404
- Notifications: PII sanitization
- Smoke manual: 15 пунктов из ТЗ + deploy doc

---

## AI Agents — зоны ответственности

| Agent | Deliverable | Проверка |
|---|---|---|
| Product | SPEC + матрица | Owner sign-off |
| UX/UI | landing 11 блоков | mobile + тексты |
| Backend | store/API/status | unit tests |
| Frontend | form.js | apply flow |
| Integrations | Sheets + Telegram | ensure script dry-run |
| Admin | list/detail/actions | POST-only status |
| QA | 28+ unit tests | pytest green |
| Security/Ops | deploy + checklist | env flags, no secrets in git |
