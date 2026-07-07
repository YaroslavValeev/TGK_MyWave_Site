"""Phase 2 — MAX / WhatsApp channel notifications."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.online_coaching_channels import (
    format_client_status_message,
    notify_client_channel,
    send_max_message,
)


@patch("app.services.online_coaching_channels.requests.post")
def test_send_max_message(mock_post):
    mock_post.return_value = MagicMock(status_code=200)
    with patch("app.services.online_coaching_channels._cfg") as mock_cfg:
        mock_cfg.side_effect = lambda k, d="": {
            "MAX_API_URL": "https://max.example/send",
            "MAX_API_TOKEN": "tok",
        }.get(k, d)
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
