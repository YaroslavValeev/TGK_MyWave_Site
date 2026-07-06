"""Telegram notification sanitization tests."""

from unittest.mock import patch

from app.services.online_coaching_notifications import (
    format_new_request_message,
    notify_new_online_request,
    sanitize_record_for_telegram,
)


def test_sanitize_masks_phone_and_health():
    safe = sanitize_record_for_telegram(
        {
            "name": "Ivan",
            "phone": "+79161234567",
            "injuries_or_limits": "больное колено",
            "goal": "стабильнее держаться",
            "preferred_channel": "telegram",
            "telegram_username": "@ivan",
        }
    )
    assert "4567" in safe["phone_masked"]
    assert "79161234567" not in safe["phone_masked"]
    assert safe["health_limits"] == "указаны"
    assert "колено" not in safe["health_limits"]


def test_new_request_message_no_full_pii():
    text = format_new_request_message(
        {
            "online_request_id": "oc_req_test1234567890",
            "service_type": "video_check",
            "name": "Ivan",
            "phone": "+79161234567",
            "preferred_channel": "telegram",
            "telegram_username": "@ivan",
            "discipline": "wakesurf",
            "level": "intermediate",
            "goal": "стабильнее держаться",
            "injuries_or_limits": "больное колено",
            "video_url": "",
            "request_status": "waiting_video",
            "payment_required_timing": "after_service",
        }
    )
    assert "колено" not in text
    assert "Ограничения по здоровью: указаны" in text
    assert "79161234567" not in text


def test_new_request_message_includes_video_url_when_present():
    url = "https://drive.google.com/file/d/abc/view"
    text = format_new_request_message(
        {
            "online_request_id": "oc_req_test1234567890",
            "service_type": "video_check",
            "name": "Ivan",
            "phone": "+79161234567",
            "preferred_channel": "telegram",
            "telegram_username": "@ivan",
            "discipline": "wakesurf",
            "level": "intermediate",
            "goal": "стабильнее держаться",
            "video_url": url,
            "request_status": "video_received",
            "payment_required_timing": "after_service",
        }
    )
    assert url in text
    assert "ссылка есть" not in text


@patch("app.services.online_coaching_notifications.send_telegram_notification_with_keyboard", return_value=True)
def test_notify_new_request_adds_open_video_button(mock_send):
    url = "https://drive.google.com/file/d/abc/view"
    record = {
        "online_request_id": "oc_req_test1234567890",
        "service_type": "video_check",
        "name": "Ivan",
        "phone": "+79161234567",
        "preferred_channel": "telegram",
        "video_url": url,
        "request_status": "video_received",
        "payment_required_timing": "after_service",
    }
    assert notify_new_online_request(record) is True
    keyboard = mock_send.call_args[0][1]
    assert any(btn.get("text") == "Открыть видео" for row in keyboard for btn in row)
    assert any(btn.get("url") == url for row in keyboard for btn in row)
