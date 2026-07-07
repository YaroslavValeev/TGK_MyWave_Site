"""Phase 2 — reminders cron."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.services.online_coaching_reminders import list_due_reminder_requests, process_due_reminders


def test_list_due_reminder_requests_filters():
    now = datetime(2026, 7, 7, 12, 0, tzinfo=timezone.utc)
    past = (now - timedelta(hours=1)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    future = (now + timedelta(hours=5)).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def fake_records(_sid, _sheet):
        return [
            {"online_request_id": "oc_req_due1", "request_status": "waiting_video", "next_followup_at": past},
            {"online_request_id": "oc_req_future", "request_status": "waiting_video", "next_followup_at": future},
            {"online_request_id": "oc_req_done", "request_status": "completed", "next_followup_at": past},
        ]

    due = list_due_reminder_requests(now=now, sheet_records=fake_records)
    assert [r["online_request_id"] for r in due] == ["oc_req_due1"]


@patch("app.services.online_coaching_reminders.log_followup_event")
@patch("app.services.online_coaching_reminders.update_request_fields")
@patch("app.services.online_coaching_reminders._notify_for_status", return_value=True)
@patch("app.services.online_coaching_reminders.list_due_reminder_requests")
def test_process_due_reminders_reschedules(mock_list, mock_notify, mock_update, mock_log):
    mock_list.return_value = [{"online_request_id": "oc_req_due1", "request_status": "waiting_payment"}]
    result = process_due_reminders(dry_run=False)
    assert result["due_count"] == 1
    assert result["processed"] == ["oc_req_due1"]
    mock_update.assert_called_once()
    mock_log.assert_called_once()
