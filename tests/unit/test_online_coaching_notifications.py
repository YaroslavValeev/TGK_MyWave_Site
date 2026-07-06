"""Telegram notification sanitization tests."""

from app.services.online_coaching_notifications import (
    format_new_request_message,
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
