"""Unit tests — Online Coaching Phase 2 (T-Bank, reminders, Telegram ingest, MAX)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services.online_coaching_channels import (
    format_client_status_message,
    is_max_configured,
    notify_client_channel,
    send_max_message,
)
from app.services.online_coaching_reminders import list_due_reminder_requests, process_due_reminders
from app.services.online_coaching_tbank import (
    build_tbank_token,
    extract_online_request_id,
    handle_tbank_notification,
    verify_notification_token,
)
from app.services.online_coaching_telegram_ingest import (
    extract_request_id_from_text,
    ingest_telegram_update,
    verify_telegram_webhook_secret,
)


def test_build_tbank_token_deterministic():
    password = "secret"
    params = {"TerminalKey": "T1", "Amount": 150000, "OrderId": "oc_test"}
    token = build_tbank_token(params, password)
    assert len(token) == 64
    assert token == build_tbank_token(params, password)


def test_verify_notification_token_valid():
    password = "pw"
    payload = {"TerminalKey": "T1", "Status": "CONFIRMED", "OrderId": "oc_oc_req_abc123_def"}
    payload["Token"] = build_tbank_token(payload, password)
    with patch("app.services.online_coaching_tbank.is_tbank_configured", return_value=True), patch(
        "app.services.online_coaching_tbank.tbank_secret_key", return_value=password
    ):
        assert verify_notification_token(payload) is True


def test_extract_online_request_id_from_data():
    payload = {"DATA": {"online_request_id": "oc_req_abc123def456"}}
    assert extract_online_request_id(payload) == "oc_req_abc123def456"


def test_extract_online_request_id_from_order_id():
    payload = {"OrderId": "oc_oc_req_abc123def456_1a2b3c4d"}
    assert extract_online_request_id(payload) == "oc_req_abc123def456"


@patch("app.services.online_coaching_tbank.mark_paid")
@patch("app.services.online_coaching_tbank.verify_notification_token", return_value=True)
def test_handle_tbank_notification_marks_paid(mock_verify, mock_mark_paid):
    mock_mark_paid.return_value = {"online_request_id": "oc_req_abc123def456"}
    payload = {
        "Status": "CONFIRMED",
        "Amount": 150000,
        "DATA": {"online_request_id": "oc_req_abc123def456"},
    }
    result = handle_tbank_notification(payload)
    assert result["action"] == "mark_paid"
    mock_mark_paid.assert_called_once()


def test_list_due_reminder_requests_filters():
    now = datetime(2026, 7, 7, 12, 0, tzinfo=timezone.utc)
    past = (now - timedelta(hours=1)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    future = (now + timedelta(hours=5)).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def fake_records(_sid, _sheet):
        return [
            {
                "online_request_id": "oc_req_due1",
                "request_status": "waiting_video",
                "next_followup_at": past,
            },
            {
                "online_request_id": "oc_req_future",
                "request_status": "waiting_video",
                "next_followup_at": future,
            },
            {
                "online_request_id": "oc_req_done",
                "request_status": "completed",
                "next_followup_at": past,
            },
        ]

    due = list_due_reminder_requests(now=now, sheet_records=fake_records)
    assert [r["online_request_id"] for r in due] == ["oc_req_due1"]


@patch("app.services.online_coaching_reminders.log_followup_event")
@patch("app.services.online_coaching_reminders.update_request_fields")
@patch("app.services.online_coaching_reminders._notify_for_status", return_value=True)
@patch("app.services.online_coaching_reminders.list_due_reminder_requests")
def test_process_due_reminders_reschedules(mock_list, mock_notify, mock_update, mock_log):
    mock_list.return_value = [
        {"online_request_id": "oc_req_due1", "request_status": "waiting_payment"},
    ]
    result = process_due_reminders(dry_run=False)
    assert result["due_count"] == 1
    assert result["processed"] == ["oc_req_due1"]
    mock_update.assert_called_once()
    mock_log.assert_called_once()


def test_extract_request_id_from_telegram_caption():
    text = "oc_req_abc123def456\nЗадача: держать баланс"
    assert extract_request_id_from_text(text) == "oc_req_abc123def456"


@patch("app.services.online_coaching_telegram_ingest.append_request_media")
@patch(
    "app.services.online_coaching_telegram_ingest.resolve_telegram_file_url",
    return_value="https://api.telegram.org/file/botX/vid.mp4",
)
def test_ingest_telegram_update(mock_url, mock_append):
    mock_append.return_value = {"online_request_id": "oc_req_abc123def456", "request_status": "video_received"}
    update = {
        "message": {
            "caption": "oc_req_abc123def456\nРазбор заезда",
            "video": {"file_id": "AAA"},
        }
    }
    result = ingest_telegram_update(update)
    assert result["online_request_id"] == "oc_req_abc123def456"
    mock_append.assert_called_once()


def test_verify_telegram_webhook_secret():
    assert verify_telegram_webhook_secret({"X-Telegram-Bot-Api-Secret-Token": "s"}, expected="s") is True
    assert verify_telegram_webhook_secret({}, expected="s") is False


@patch("app.services.online_coaching_channels.requests.post")
def test_send_max_message(mock_post):
    mock_post.return_value = MagicMock(status_code=200)
    with patch("app.services.online_coaching_channels._cfg") as mock_cfg:
        mock_cfg.side_effect = lambda k, d="": {"MAX_API_URL": "https://max.example/send", "MAX_API_TOKEN": "tok"}.get(k, d)
        ok = send_max_message("+79990001122", "hello")
    assert ok is True


def test_notify_client_channel_skips_without_api():
    record = {"preferred_channel": "max", "max_contact": "@user", "online_request_id": "oc_req_x"}
    with patch("app.services.online_coaching_channels.is_max_configured", return_value=False):
        result = notify_client_channel(record, event="application_received")
    assert result["skipped"] is True


def test_format_client_status_message():
    msg = format_client_status_message(
        {"name": "Иван", "service_type": "video_check", "online_request_id": "oc_req_x", "request_status": "new"},
        event="application_received",
    )
    assert "Иван" in msg
    assert "oc_req_x" in msg
