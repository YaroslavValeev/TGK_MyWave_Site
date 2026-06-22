"""PR53 evidence tests — message contracts, mobile markup, storage."""

import pytest
from unittest.mock import patch

from app.routes.shop import PRODUCT_REQUEST_SUCCESS_MESSAGE
from app.services.application_notifications import format_application_telegram_message
from app.services.product_leads import ProductLeadResult, PRODUCT_LEADS_HEADERS


FORBIDDEN_USER_PHRASES = (
    "товар куплен",
    "заказ подтвержд",
    "оплачено",
    "доставка оформлена",
)

EXPECTED_SUCCESS = PRODUCT_REQUEST_SUCCESS_MESSAGE


def test_product_telegram_message_full_contract():
    """Owner §3: Telegram template fields without secrets."""
    text = format_application_telegram_message(
        "product",
        {
            "name": "Мария",
            "phone": "+7 916 123 45 67",
            "telegram": "@maria",
            "email": "maria@example.com",
            "product_title": "Баланс-борд",
            "product_id": "balance-board",
            "quantity": 1,
            "comment": "Нужен самовывоз",
            "source": "product",
            "page_url": "https://mywavewake.ru/shop/product/balance-board",
            "status": "new",
        },
    )
    for line in (
        "Новая заявка: Заявка на товар",
        "Имя: Мария",
        "Телефон: +7 916 123 45 67",
        "Telegram: @maria",
        "Email: maria@example.com",
        "Проект/услуга: Баланс-борд",
        "Комментарий: Нужен самовывоз",
        "Источник: product",
        "Страница: https://mywavewake.ru/shop/product/balance-board",
        "Статус: new",
    ):
        assert line in text, f"missing: {line}"


def test_product_leads_sheet_headers_contract():
    assert PRODUCT_LEADS_HEADERS == [
        "lead_id",
        "name",
        "phone",
        "telegram",
        "email",
        "product_id",
        "product_title",
        "quantity",
        "comment",
        "page_url",
        "source",
        "status",
        "created_at",
    ]


@patch("app.routes.shop.notify_new_application")
@patch("app.routes.shop.save_product_lead")
def test_product_request_success_message_exact(mock_save, mock_notify, client):
    mock_save.return_value = ProductLeadResult(
        lead_id="prod_lead_evidence",
        status="new",
        sheet_name="Product_Leads",
    )
    rv = client.post(
        "/shop/api/product-request",
        json={
            "name": "Test User",
            "phone": "+7 916 111 22 33",
            "product_id": "balance-board",
            "product_title": "Баланс-борд",
            "quantity": 1,
        },
    )
    body = rv.get_json()
    assert body["message"] == EXPECTED_SUCCESS
    for phrase in FORBIDDEN_USER_PHRASES:
        assert phrase not in body["message"].lower()


@patch("app.routes.shop.save_product_lead", side_effect=RuntimeError("sheets down"))
def test_product_request_error_message_no_false_purchase(mock_save, client):
    rv = client.post(
        "/shop/api/product-request",
        json={
            "name": "Test User",
            "phone": "+7 916 111 22 33",
            "product_id": "balance-board",
            "product_title": "Баланс-борд",
        },
    )
    body = rv.get_json()
    assert rv.status_code == 500
    assert body["ok"] is False
    for phrase in FORBIDDEN_USER_PHRASES:
        assert phrase not in (body.get("error") or "").lower()


@patch("app.routes.shop.notify_new_application", return_value=False)
@patch("app.routes.shop.save_product_lead")
def test_telegram_failure_does_not_break_lead(mock_save, mock_notify, client):
    """Owner §3: graceful fallback when Telegram fails."""
    mock_save.return_value = ProductLeadResult(
        lead_id="prod_lead_tg_fail",
        status="new",
        sheet_name="Product_Leads",
    )
    rv = client.post(
        "/shop/api/product-request",
        json={
            "name": "Test",
            "phone": "+7 916 000 00 01",
            "product_id": "wave-cards",
            "product_title": "Wave Cards",
        },
    )
    assert rv.status_code == 200
    assert rv.get_json()["ok"] is True
    mock_notify.assert_called_once()


def test_booking_modals_have_back_step_buttons(client):
    """Mobile UX: ← Назад uses btn-back-step, not close-modal btn."""
    html = client.get("/").get_data(as_text=True)
    assert 'class="btn-back-step"' in html
    assert 'data-back-step="1"' in html
    assert 'data-back-step="2"' in html
    assert "← Назад" in html


def test_product_request_modal_markup(client):
    html = client.get("/shop/product/balance-board").get_data(as_text=True)
    assert 'id="modalProductRequest"' in html
    assert 'id="product-request-form"' in html
    assert "data-product-request" in html
    assert "Онлайн-оплата для этого товара пока не подключена" in html
    for phrase in FORBIDDEN_USER_PHRASES:
        assert phrase not in html.lower()


def test_booking_mobile_css_linked(client):
    html = client.get("/").get_data(as_text=True)
    assert "booking-mobile.css" in html


def test_booking_mobile_css_contains_compact_rules():
    from pathlib import Path

    css = Path("static/css/booking-mobile.css").read_text(encoding="utf-8")
    for needle in (
        "@media (max-width: 768px)",
        ".slot-btn",
        ".boat-set-btn",
        ".btn-back-step",
        "modal-content--compact",
    ):
        assert needle in css
