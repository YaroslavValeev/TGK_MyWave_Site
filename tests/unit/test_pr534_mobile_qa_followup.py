"""PR53.4 — mobile carousel autoplay, footer social link, Telegram status sanitize."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.application_notifications import format_application_telegram_message


FORBIDDEN_NOTIFY_FRAGMENTS = ("MagicMock", "<MagicMock", "object at 0x")


def test_competitions_ticker_mobile_autoscroll_enabled():
    js = Path("static/js/competitions-ticker.js").read_text(encoding="utf-8")
    css = Path("static/css/competitions-ticker.css").read_text(encoding="utf-8")
    assert "is-autoplay" in js
    assert "competitions-ticker-marquee" in css
    assert "--ticker-duration" in js


def test_index_loads_competitions_ticker_v8(client):
    html = client.get("/").get_data(as_text=True)
    assert "competitions-ticker.js?v=8" in html
    assert "competitions-ticker.css?v=8" in html


def test_footer_shows_social_responsibility_link_when_module_enabled(client, monkeypatch):
    monkeypatch.setenv("SOCIAL_MODULE_ENABLED", "1")
    html = client.get("/").get_data(as_text=True)
    assert "site-footer__link" in html
    assert "Социальная ответственность" in html
    assert 'href="/social"' in html


def test_telegram_status_rejects_magicmock():
    mock_status = MagicMock(name="save_product_lead().status")
    text = format_application_telegram_message(
        "product",
        {
            "name": "Test",
            "phone": "+7 916 000 00 01",
            "product_title": "Board",
            "status": mock_status,
        },
    )
    assert "Статус: new" in text
    for frag in FORBIDDEN_NOTIFY_FRAGMENTS:
        assert frag not in text


def test_telegram_service_lead_status_human_readable():
    text = format_application_telegram_message(
        "camp",
        {
            "name": "Anna",
            "phone": "+7 916 000 00 02",
            "comment": "Хочу в camp",
            "source": "camp",
            "status": "new",
        },
    )
    assert "Статус: new" in text
    for frag in FORBIDDEN_NOTIFY_FRAGMENTS:
        assert frag not in text


@patch("app.routes.shop.notify_new_application")
@patch("app.routes.shop.save_product_lead")
def test_product_notify_payload_uses_literal_new_status(mock_save, mock_notify, client):
    mock_save.return_value = MagicMock(
        lead_id="prod_x",
        status=MagicMock(name="save_product_lead().status"),
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
    assert rv.status_code == 200
    notify_payload = mock_notify.call_args[0][1]
    assert notify_payload["status"] == "new"


def test_branding_css_mobile_footer_clearance():
    css = Path("static/css/branding.css").read_text(encoding="utf-8")
    assert "site-footer__nav" in css
    assert "site-footer__link" in css
    assert "safe-area-inset-bottom" in css
