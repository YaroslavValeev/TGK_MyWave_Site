# PR53 Evidence Package

Branch: `feature/pr53-mobile-product-notifications`  
Commit: `e6fd29ca` (+ evidence commit pending)  
PR: https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/53

## Mobile UX screenshots

Captured locally via `scripts/pr53_capture_evidence.py` (Playwright, Flask `127.0.0.1:5000`).

| Viewport | Files |
|----------|-------|
| 390×844 | `screenshots/mobile_390x844_*.png` |
| 360×800 | `screenshots/mobile_360x800_*.png` |
| 1366×768 desktop | `screenshots/desktop_1366x768_*.png` |

Coverage:
- `*_01_booking_step1*` — шаг 1, выбор даты
- `*_02_booking_step2_slots*` — шаг 2, список слотов
- `*_03_booking_back_button*` — кнопка «← Назад»
- `*_04_booking_set_count*` — селектор количества сетов (boat)
- Desktop booking + product page without mobile regressions

Note: slots/set-count frames use controlled modal state for reproducible capture when live slot API is unavailable locally.

## Product purchase flow

| Step | Screenshot |
|------|------------|
| Карточка / «Купить» | `*_05_product_card.png` |
| Пустая модалка | `*_06_product_modal_empty.png` |
| Заполненная форма | `*_07_product_modal_filled.png` |
| Success message | `*_08_product_success.png` |
| Error state | `*_09_product_error.png` |

Success copy (exact): «Заявка отправлена. Мы уточним наличие товара и свяжемся с вами для подтверждения заказа.»

Forbidden phrases absent in UI/tests: «товар куплен», «заказ подтверждён», «оплачено», «доставка оформлена».

## Telegram proof

- Template: `telegram_message_sample.txt`
- Automated: `tests/unit/test_application_notifications.py`, `tests/unit/test_pr53_evidence.py::test_product_telegram_message_full_contract`
- Graceful fallback: `test_telegram_failure_does_not_break_lead`, `test_notify_failure_does_not_raise`
- Live dev/staging chat screenshot: **Owner QA** (bot token not in repo)

## Storage proof

- Primary: Google Sheet `Product_Leads` (headers in `test_product_leads_sheet_headers_contract`)
- Fallback: structured log `product_lead_saved` / `product_lead_save_failed` when sheet unavailable
- Tests: `tests/unit/test_product_leads.py`, `tests/unit/test_shop_product_request.py`

## Out of scope confirmation

Not changed in PR53 diff vs `main` (`e35ea6ff`):

- `.env` (prod)
- prod config / systemd
- booking capacity logic
- chat / KB / TGbotAdmin
- migrations
- frontend beyond PR53 scope

## Tests

```bash
pytest tests/unit/test_application_notifications.py \
       tests/unit/test_product_leads.py \
       tests/unit/test_shop_product_request.py \
       tests/unit/test_pr53_evidence.py -q
```

Expected: **20 passed**

Deploy status: **NOT STARTED**
