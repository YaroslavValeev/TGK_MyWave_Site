"""Analytics /api/log triggers service lead notification (PR53.1)."""

from unittest.mock import patch


@patch("app.services.application_notifications.notify_service_lead_from_analytics", return_value=True)
@patch("app.services.google_sheets_service.log_analytics_event", return_value=True)
def test_analytics_camp_lead_triggers_notify(mock_log, mock_notify, client):
    rv = client.post(
        "/analytics/log",
        json={
            "event": "camp_lead",
            "label": "camp",
            "phone": "+7 916 222 33 44",
            "meta": {
                "service": "camp",
                "name": "Мария",
                "phone": "+7 916 222 33 44",
                "goal": "Camp",
            },
        },
    )
    assert rv.status_code == 200
    assert rv.get_json()["ok"] is True
    mock_notify.assert_called_once()
