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
    assert "balance-board" in text


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


def test_format_web_booking_message():
    from app.services.application_notifications import format_web_booking_telegram_message

    text = format_web_booking_telegram_message(
        {
            "name": "Анна",
            "phone": "+79160001122",
            "service_type": "boat",
            "date": "2026-08-30",
            "time": "10:00",
            "booking_id": "bk_test1",
            "workout_id": "yc-123",
        }
    )
    assert "Новая запись с сайта: Катер" in text
    assert "Анна" in text
    assert "2026-08-30" in text
    assert "10:00" in text
    assert "bk_test1" in text


@patch("app.services.application_notifications.send_telegram_notification", return_value=True)
def test_notify_web_booking_uses_web_booking_type(mock_send):
    from app.services.application_notifications import notify_web_booking

    ok = notify_web_booking(
        {
            "name": "Анна",
            "phone": "+79160001122",
            "service_type": "gym",
            "date": "2026-08-30",
            "time": "18:00",
        }
    )
    assert ok is True
    mock_send.assert_called_once()
    message = mock_send.call_args[0][2]
    assert "Новая запись с сайта: Зал" in message
