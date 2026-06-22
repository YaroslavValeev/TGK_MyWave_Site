"""PR53.1 — service lead Telegram via analytics/log."""

from unittest.mock import patch

from app.services.application_notifications import (
    notify_service_lead_from_analytics,
)


@patch("app.services.application_notifications.notify_new_application", return_value=True)
def test_camp_lead_from_analytics(mock_notify):
    ok = notify_service_lead_from_analytics(
        "camp_lead",
        {"name": "Иван", "phone": "+7 916 111 22 33", "service": "camp", "goal": "трюки"},
        phone="+7 916 111 22 33",
    )
    assert ok is True
    mock_notify.assert_called_once()
    args = mock_notify.call_args[0]
    assert args[0] == "camp"
    assert args[1]["name"] == "Иван"


@patch("app.services.application_notifications.notify_new_application")
def test_unknown_event_skipped(mock_notify):
    ok = notify_service_lead_from_analytics("page_view", {"name": "X", "phone": "+7999"})
    assert ok is False
    mock_notify.assert_not_called()


@patch("app.services.application_notifications.notify_new_application")
def test_missing_contact_skipped(mock_notify):
    ok = notify_service_lead_from_analytics("coach_lead", {"service": "coach_triper"})
    assert ok is False
    mock_notify.assert_not_called()
