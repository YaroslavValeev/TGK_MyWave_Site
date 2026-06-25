"""PR55 — Social 2.0 MVP: page, form, Social_Applications, sanitized Telegram."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.application_notifications import (
    format_social_telegram_message,
    notify_new_application,
)
from app.services.social_store import validate_application_payload


def _valid_payload(**overrides):
    base = {
        "parent_name": "Иван Иванов",
        "parent_phone": "+7 916 000 00 00",
        "child_first_name": "Алексей",
        "child_age": 12,
        "preferred_contact": "phone",
        "consent_personal_data": True,
        "consent_training": True,
        "consent_version": "2026-06-v1",
    }
    base.update(overrides)
    return base


@pytest.fixture
def social_flags_on(monkeypatch):
    monkeypatch.setenv("SOCIAL_MODULE_ENABLED", "1")
    monkeypatch.setenv("SOCIAL_WIDGET_ENABLED", "1")
    monkeypatch.setenv("SOCIAL_APPLICATIONS_ENABLED", "1")
    monkeypatch.setenv("SOCIAL_ADMIN_NOTIFICATIONS_ENABLED", "1")
    monkeypatch.setenv("SOCIAL_PUBLIC_STATS_ENABLED", "0")
    monkeypatch.setenv("SOCIAL_BOOKING_ENABLED", "0")


def test_social_page_returns_200(client, social_flags_on):
    resp = client.get("/social")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "MyWave Social 2.0" in html
    assert "не бронирует" in html


def test_social_form_rendered(client, social_flags_on):
    html = client.get("/social").get_data(as_text=True)
    assert 'id="social-application-form"' in html
    assert 'name="parent_name"' in html
    assert 'name="motivation_text"' in html


def test_social_public_stats_off_on_page(client, social_flags_on):
    html = client.get("/social").get_data(as_text=True)
    assert "social-stats-card" not in html


def test_forbidden_booking_keys_rejected():
    errors = validate_application_payload(_valid_payload(booking_id="x", slot="10:00"))
    assert any("forbidden_field" in e for e in errors)


def test_telegram_contact_requires_username():
    errors = validate_application_payload(
        _valid_payload(
            preferred_contact="telegram",
            parent_phone="",
            telegram_username="",
        )
    )
    assert "required:telegram_username" in errors


def test_format_social_telegram_no_health_notes():
    text = format_social_telegram_message(
        {
            "application_id": "soc_app_test",
            "parent_name": "Мария",
            "parent_phone": "+7 916 111 22 33",
            "child_age": 10,
            "city": "Москва",
            "has_safety_info": True,
            "health_notes": "секретные медицинские детали",
            "motivation_text": "длинный комментарий",
            "page_url": "https://mywavewake.ru/social",
            "status": "new",
        }
    )
    assert "soc_app_test" in text
    assert "Важная информация для безопасности: да" in text
    assert "медицинские" not in text
    assert "длинный комментарий" not in text
    assert "MagicMock" not in text


def test_format_social_telegram_rejects_magicmock_status():
    text = format_social_telegram_message(
        {
            "application_id": "soc_app_x",
            "parent_name": "Test",
            "parent_phone": "+79990001122",
            "status": MagicMock(),
        }
    )
    assert "Статус: new" in text
    assert "MagicMock" not in text


@patch("app.routes.social.notify_new_application", return_value=True)
@patch("app.routes.social.append_social_application")
def test_apply_save_then_notify(mock_append, mock_notify, client, social_flags_on):
    from app.services.social_store import SocialWriteResult

    mock_append.return_value = SocialWriteResult(
        application_id="soc_app_notify",
        status="new",
        sheet_name="Social_Applications",
    )
    rv = client.post("/api/social/apply", json=_valid_payload())
    assert rv.status_code == 201
    assert rv.get_json()["application_id"] == "soc_app_notify"
    assert rv.get_json()["status"] == "new"
    mock_append.assert_called_once()
    mock_notify.assert_called_once()
    assert mock_notify.call_args[0][0] == "social"
    payload = mock_notify.call_args[0][1]
    assert payload["application_id"] == "soc_app_notify"
    assert "health_notes" not in payload


@patch("app.routes.social.notify_new_application", side_effect=RuntimeError("tg fail"))
@patch("app.routes.social.append_social_application")
def test_apply_telegram_failure_still_succeeds(mock_append, mock_notify, client, social_flags_on):
    from app.services.social_store import SocialWriteResult

    mock_append.return_value = SocialWriteResult(
        application_id="soc_app_ok",
        status="new",
        sheet_name="Social_Applications",
    )
    rv = client.post("/api/social/apply", json=_valid_payload())
    assert rv.status_code == 201
    assert rv.get_json()["ok"] is True


@patch("app.routes.social.notify_new_application")
def test_notify_skipped_when_admin_notifications_off(mock_notify, client, social_flags_on, monkeypatch):
    from app.services.social_store import SocialWriteResult

    monkeypatch.setenv("SOCIAL_ADMIN_NOTIFICATIONS_ENABLED", "0")
    with patch(
        "app.routes.social.append_social_application",
        return_value=SocialWriteResult(
            application_id="soc_app_no_tg",
            status="new",
            sheet_name="Social_Applications",
        ),
    ):
        rv = client.post("/api/social/apply", json=_valid_payload())
    assert rv.status_code == 201
    mock_notify.assert_not_called()


@patch("app.routes.social.append_social_application")
def test_apply_no_booking_calendar_writes(mock_append, client, social_flags_on, mocker):
    from app.services.social_store import SocialWriteResult

    booking_spy = mocker.patch("app.routes.api.real_book_slot")
    mock_append.return_value = SocialWriteResult(
        application_id="soc_app_x",
        status="new",
        sheet_name="Social_Applications",
    )
    client.post("/api/social/apply", json=_valid_payload())
    booking_spy.assert_not_called()


@patch("app.services.application_notifications.send_telegram_notification", return_value=True)
def test_notify_new_application_social_type(mock_send):
    notify_new_application(
        "social",
        {
            "application_id": "soc_app_abc",
            "parent_name": "Anna",
            "parent_phone": "+79990001122",
            "child_age": 11,
            "has_safety_info": False,
            "page_url": "/social",
            "status": "new",
        },
    )
    message = mock_send.call_args[0][2]
    assert "MyWave Social" in message
    assert "soc_app_abc" in message
    assert "BOT_TOKEN" not in message


def test_pr54_regression_health(client):
    assert client.get("/health/live").status_code == 200
