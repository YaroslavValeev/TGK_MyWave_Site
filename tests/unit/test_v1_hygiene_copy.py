"""v1 hygiene copy: honest shop/chat/success, no fake checkout."""

from pathlib import Path


def test_home_uses_telegram_cta_not_trainer_chat(client):
    html = client.get("/").get_data(as_text=True)
    assert "Написать в Telegram" in html
    assert "Чат с тренером" not in html
    assert "Оставить заявку" in html
    assert ">Купить<" not in html


def test_shop_is_made_to_order_not_checkout(client):
    html = client.get("/shop/").get_data(as_text=True)
    assert "Товары на заказ" in html
    assert "Онлайн-магазин" not in html
    assert "Оставить заявку" in html
    assert ">Купить<" not in html


def test_product_page_request_cta(client):
    html = client.get("/shop/product/balance-board").get_data(as_text=True)
    assert "Оставить заявку" in html
    assert "Вернуться к товарам" in html
    assert "Онлайн-оплата для этого товара пока не подключена" in html


def test_chat_widget_is_helper_not_live_trainer(client):
    html = client.get("/").get_data(as_text=True)
    assert "Помощник MyWave" in html
    assert "Чат с экспертом по вейку" not in html


def test_chat_page_honest_copy(client):
    html = client.get("/chat/").get_data(as_text=True)
    assert "Помощник MyWave" in html
    assert "Живой тренер здесь не сидит" in html
    assert "@MyW23" in html


def test_booking_success_view_has_contacts_not_payment(client):
    html = client.get("/booking/success-view?type=boat").get_data(as_text=True)
    assert "Запись на катер подтверждена" in html
    assert "+7 (916) 011-71-79" in html
    assert "@MyW23" in html
    assert "Мы получили вашу запись" in html
    # Контент шага после записи — без реквизитов (оплата вне этого релиза).
    card_start = html.find("success-card")
    card = html[card_start : card_start + 2500] if card_start >= 0 else html
    assert "реквизит" not in card.lower()
    assert "т-банк" not in card.lower()


def test_booking_js_success_modal_has_contacts():
    js = Path("static/js/booking.js").read_text(encoding="utf-8")
    assert "tel:+79160117179" in js
    assert "https://t.me/MyW23" in js
    assert "Мы получили вашу запись" in js


def test_chat_js_welcome_is_kb_first():
    js = Path("static/js/chat.js").read_text(encoding="utf-8")
    assert "базе знаний" in js
    assert "проведу через запись на слот" not in js
