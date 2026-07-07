"""Phase 2 — T-Bank API."""

from __future__ import annotations

from unittest.mock import patch

from app.services.online_coaching_tbank import (
    build_tbank_token,
    extract_online_request_id,
    handle_tbank_notification,
    verify_notification_token,
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
    payload = {"Status": "CONFIRMED", "Amount": 150000, "DATA": {"online_request_id": "oc_req_abc123def456"}}
    result = handle_tbank_notification(payload)
    assert result["action"] == "mark_paid"
    mock_mark_paid.assert_called_once()
