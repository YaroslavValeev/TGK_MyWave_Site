"""PR56/PR68 — sanitized Telegram regression for Social manual assign."""

from unittest.mock import patch

import pytest

from app.services.application_notifications import (
    format_social_session_scheduled_message,
    format_social_telegram_message,
    notify_social_session_scheduled,
)

# Substrings that must never appear in session-scheduled admin Telegram.
_SESSION_FORBIDDEN = (
    "health_notes",
    "диагноз",
    "allergy",
    "аллерг",
    "Иванов",
    "+7 916",
    "parent_name",
    "parent_phone",
    "motivation_text",
    "internal_notes",
    "coach_secret",
    "MagicMock",
)


def _rich_sensitive_payload() -> dict:
    return {
        "application_id": "soc_app_e7be01a15ded4365",
        "session_id": "soc_sess_e41e448019644a73",
        "session_date": "2026-07-15",
        "session_time": "10:00",
        "location": "Зал MyWave",
        "status": "scheduled",
        "coach": "coach_secret",
        "service_type": "boat",
        "notes": "диагноз и внутренний комментарий",
        "health_notes": "allergy peanuts",
        "parent_name": "Иванов Иван",
        "parent_phone": "+7 916 000 00 00",
        "motivation_text": "хочу на вейк",
        "internal_notes": "не для Telegram",
    }


class TestSessionScheduledTelegramRegression:
    def test_allowed_fields_present(self):
        text = format_social_session_scheduled_message(_rich_sensitive_payload())
        assert "soc_app_e7be01a15ded4365" in text
        assert "soc_sess_e41e448019644a73" in text
        assert "2026-07-15" in text
        assert "10:00" in text
        assert "Зал MyWave" in text
        assert "status=scheduled" in text

    @pytest.mark.parametrize("forbidden", _SESSION_FORBIDDEN)
    def test_sensitive_substrings_excluded(self, forbidden):
        text = format_social_session_scheduled_message(_rich_sensitive_payload())
        assert forbidden not in text

    def test_notes_field_not_included_even_when_present(self):
        text = format_social_session_scheduled_message(
            {"application_id": "soc_app_x", "session_id": "soc_sess_y", "notes": "секрет"}
        )
        assert "секрет" not in text
        assert "notes" not in text.lower()

    def test_coach_and_service_type_not_included(self):
        text = format_social_session_scheduled_message(
            {
                "application_id": "soc_app_x",
                "session_id": "soc_sess_y",
                "coach": "Тренер А",
                "service_type": "wake",
            }
        )
        assert "Тренер А" not in text
        assert "wake" not in text

    @patch("app.services.application_notifications.send_telegram_notification", return_value=True)
    def test_notify_path_message_sanitized(self, mock_send):
        notify_social_session_scheduled(_rich_sensitive_payload())
        message = mock_send.call_args[0][2]
        for forbidden in _SESSION_FORBIDDEN:
            assert forbidden not in message
        assert "soc_app_e7be01a15ded4365" in message


class TestSocialApplicationTelegramRegression:
    def test_new_application_message_excludes_health_notes_body(self):
        text = format_social_telegram_message(
            {
                "application_id": "soc_app_new",
                "parent_name": "Мария",
                "parent_phone": "+7 900 111 22 33",
                "health_notes": "секретные медицинские детали",
                "has_safety_info": True,
                "status": "new",
            }
        )
        assert "секретные медицинские детали" not in text
        assert "health_notes" not in text
        assert "Важная информация для безопасности: да" in text
