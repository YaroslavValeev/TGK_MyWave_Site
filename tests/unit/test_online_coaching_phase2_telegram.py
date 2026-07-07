"""Phase 2 — Telegram video ingest."""

from __future__ import annotations

from unittest.mock import patch

from app.services.online_coaching_telegram_ingest import (
    extract_request_id_from_text,
    ingest_telegram_update,
    verify_telegram_webhook_secret,
)


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
    update = {"message": {"caption": "oc_req_abc123def456\nРазбор заезда", "video": {"file_id": "AAA"}}}
    result = ingest_telegram_update(update)
    assert result["online_request_id"] == "oc_req_abc123def456"
    mock_append.assert_called_once()


def test_verify_telegram_webhook_secret():
    assert verify_telegram_webhook_secret({"X-Telegram-Bot-Api-Secret-Token": "s"}, expected="s") is True
    assert verify_telegram_webhook_secret({}, expected="s") is False
