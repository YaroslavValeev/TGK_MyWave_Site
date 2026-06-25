"""PR53.1 — service lead Telegram via analytics/log."""

from unittest.mock import MagicMock, patch

from app.services.application_notifications import (
    notify_service_lead_from_analytics,
)


@patch("app.services.project_applications.submit_project_application")
def test_camp_lead_from_analytics(mock_submit):
    mock_submit.return_value = MagicMock(notification_status="sent")
    ok = notify_service_lead_from_analytics(
        "camp_lead",
        {"name": "Иван", "phone": "+7 916 111 22 33", "service": "camp", "goal": "трюки"},
        phone="+7 916 111 22 33",
    )
    assert ok is True
    mock_submit.assert_called_once()
    assert mock_submit.call_args[0][0] == "camp"


@patch("app.services.project_applications.submit_project_application")
def test_unknown_event_skipped(mock_submit):
    ok = notify_service_lead_from_analytics("page_view", {"name": "X", "phone": "+7999"})
    assert ok is False
    mock_submit.assert_not_called()


@patch("app.services.project_applications.submit_project_application")
def test_missing_contact_skipped(mock_submit):
    ok = notify_service_lead_from_analytics("coach_lead", {"service": "coach_triper"})
    assert ok is False
    mock_submit.assert_not_called()
