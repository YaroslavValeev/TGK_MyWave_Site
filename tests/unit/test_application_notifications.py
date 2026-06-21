"""Unit tests for unified application notifications (PR53)."""

from unittest.mock import patch

from app.services.application_notifications import (
    format_application_telegram_message,
    notify_new_application,
)


def test_format_product_application_message():
    text = format_application_telegram_message(
        "product",
        {
            "name": "Иван",
            "phone": "+7 916 000 00 00",
            "product_title": "Баланс-борд",
            "product_id": "balance-board",
            "quantity": 2,
            "source": "product",
            "page_url": "https://mywavewake.ru/shop/product/balance-board",
            "status": "new",
        },
    )
    assert "Заявка на товар" in text
    assert "Иван" in text
    assert "Баланс-борд" in text
    assert "Количество: 2" in text


@patch("app.services.application_notifications.send_telegram_notification", return_value=True)
def test_notify_new_application_best_effort(mock_send):
    ok = notify_new_application(
        "product",
        {"name": "Test", "phone": "+79990001122", "product_title": "Wave Cards"},
    )
    assert ok is True
    mock_send.assert_called_once()


@patch("app.services.application_notifications.send_telegram_notification", side_effect=RuntimeError("network"))
def test_notify_failure_does_not_raise(mock_send):
    ok = notify_new_application("product", {"name": "Test", "phone": "+79990001122"})
    assert ok is False
