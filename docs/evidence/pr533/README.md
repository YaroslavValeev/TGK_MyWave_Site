# PR53.3 — Product storefront polish

## Changes
- Poncho: **14 500 ₽**
- Certificate title: **Сертификат (на занятия в зале)**
- WakeSurf Polia: **10 000 ₽**
- Buyer success message: individual production, no warehouse, Yandex Market PVZ, ~7 days
- Modal hint aligned with success message

## Forbidden phrases (must NOT appear in user-facing copy)
- товар куплен
- заказ подтверждён
- оплачено
- доставка оформлена

## Tests
```bash
pytest tests/unit/test_shop_product_copy.py tests/unit/test_pr53_evidence.py tests/unit/test_shop_product_request.py -q
```

## Screenshots (Owner QA)
Capture after merge/staging:
- [ ] `/shop` — product list prices
- [ ] `/shop/product/poncho` — card + price
- [ ] `/shop/product/sertificate` — certificate title «в зале»
- [ ] `/shop/product/wakesurfpolia` — 10 000 ₽
- [ ] Product request modal — hint text
- [ ] Mobile 360px — same pages

Deploy status: **NOT STARTED**
