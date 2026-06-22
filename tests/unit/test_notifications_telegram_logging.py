"""Sanitized Telegram notification logging (PR53.1)."""

from unittest.mock import MagicMock, patch

from app.services.notifications import send_telegram_notification


@patch("app.services.notifications._telegram_bot_token", return_value="")
@patch("app.services.notifications._telegram_chat_id", return_value="123")
def test_telegram_skipped_without_token(mock_chat, mock_token):
    ok = send_telegram_notification("Test", "+79990001122", "hello")
    assert ok is False


@patch("app.services.notifications.requests.post")
@patch("app.services.notifications._telegram_bot_token", return_value="secret-token")
@patch("app.services.notifications._telegram_chat_id", return_value="123")
def test_telegram_failure_sanitized_log(mock_chat, mock_token, mock_post):
    resp = MagicMock()
    resp.ok = False
    resp.status_code = 403
    resp.text = "secret-token forbidden"
    mock_post.return_value = resp

    ok = send_telegram_notification("Test", "+79990001122", "msg")
    assert ok is False
