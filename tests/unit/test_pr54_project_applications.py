"""PR54 — legal pages, Project_Applications, unified project notifications."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.application_notifications import (
    format_application_telegram_message,
    notify_new_application,
    notify_service_lead_from_analytics,
)
from app.services.project_applications import (
    PROJECT_APPLICATIONS_HEADERS,
    build_project_application_row,
    save_project_application,
    submit_project_application,
    try_submit_from_analytics_event,
    validate_project_application,
)


@pytest.mark.parametrize(
    "path",
    [
        "/legal/personal-data-consent",
        "/legal/media-consent",
        "/legal/wake-challenge-consent",
    ],
)
def test_legal_consent_routes_return_200(client, path):
    resp = client.get(path)
    assert resp.status_code == 200
    assert "legal-page" in resp.get_data(as_text=True)


def test_wake_challenge_coach_form_has_consent_link(client):
    resp = client.get("/projects/wakesurf-challenge-2025")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'name="consent_personal_data"' in html
    assert ">согласия</a>" in html or "согласия</a>" in html
    assert "/legal/personal-data-consent" in html


def test_project_applications_headers_contract():
    assert PROJECT_APPLICATIONS_HEADERS[0] == "application_id"
    assert "notification_status" in PROJECT_APPLICATIONS_HEADERS
    assert "utm_campaign" in PROJECT_APPLICATIONS_HEADERS


def test_validate_project_application_requires_contact():
    assert "invalid:contact" in validate_project_application(
        {"name": "Иван", "application_type": "camp"}
    )


def test_build_project_application_row_order():
    row = build_project_application_row(
        "proj_app_test",
        {
            "application_type": "wake_challenge",
            "name": "Coach",
            "phone": "+7 916 000 00 00",
            "consent_personal_data": True,
            "consent_media": True,
        },
    )
    assert row[0] == "proj_app_test"
    assert row[4] == "wake_challenge"
    assert row[13] == "yes"


def test_save_project_application_local_only(app):
    with app.app_context():
        result, row_num = save_project_application(
            {
                "application_type": "wake_challenge",
                "name": "Тренер",
                "phone": "+7 916 111 22 33",
            },
            sheet_append=None,
        )
    assert result.application_id.startswith("proj_app_")
    assert result.status == "new"
    assert result.notification_status == "pending"
    assert row_num is None


@patch("app.services.application_notifications.notify_new_application", return_value=True)
def test_submit_project_application_save_before_notify(mock_notify, app):
    order = []

    def _append(sid, sheet, values):
        order.append("save")
        return {"updates": {"updatedRange": "Project_Applications!A10:T10"}}

    with app.app_context():
        result = submit_project_application(
            "wake_challenge",
            {
                "name": "Тренер",
                "phone": "+7 916 111 22 33",
                "email": "c@test.ru",
                "comment": "coach",
            },
            sheet_append=_append,
            sheet_update=lambda *a, **k: None,
        )

    assert order == ["save"]
    mock_notify.assert_called_once()
    assert mock_notify.call_args[0][0] == "wake_challenge"
    assert result.notification_status == "sent"


@patch("app.services.application_notifications.notify_new_application", return_value=False)
def test_submit_project_application_telegram_failure_graceful(mock_notify, app):
    with app.app_context():
        result = submit_project_application(
            "wake_challenge",
            {"name": "Тренер", "phone": "+7 916 111 22 33"},
            sheet_append=lambda *a, **k: None,
        )
    assert result.application_id.startswith("proj_app_")
    assert result.notification_status == "failed_or_skipped"


@patch("app.services.application_notifications.notify_new_application", side_effect=RuntimeError("tg down"))
def test_submit_project_application_telegram_exception_graceful(mock_notify, app):
    with app.app_context():
        result = submit_project_application(
            "camp",
            {"name": "Иван", "phone": "+7 916 111 22 33"},
            sheet_append=lambda *a, **k: None,
        )
    assert result.notification_status == "failed"
    assert "tg down" in result.notification_error


def test_notification_text_no_magicmock():
    mock_status = MagicMock()
    text = format_application_telegram_message(
        "wake_challenge",
        {
            "application_id": "proj_app_abc",
            "name": "Test",
            "phone": "+79990001122",
            "comment": mock_status,
            "status": mock_status,
        },
    )
    lowered = text.lower()
    assert "magicmock" not in lowered
    assert "proj_app_abc" in text
    assert "Статус: new" in text


@patch("app.services.application_notifications.send_telegram_notification", return_value=True)
def test_notify_new_application_includes_application_type(mock_send):
    notify_new_application(
        "wake_challenge",
        {
            "application_id": "proj_app_x",
            "name": "Coach",
            "phone": "+79990001122",
            "comment": "coach application",
            "status": "new",
        },
    )
    message = mock_send.call_args[0][2]
    assert "Wake Challenge" in message
    assert "proj_app_x" in message
    assert "BOT_TOKEN" not in message


@patch("app.services.project_applications.submit_project_application")
def test_analytics_camp_lead_uses_project_applications(mock_submit):
    mock_submit.return_value = MagicMock(notification_status="sent")
    ok = notify_service_lead_from_analytics(
        "camp_lead",
        {"name": "Иван", "phone": "+7 916 111 22 33", "service": "camp"},
        phone="+7 916 111 22 33",
    )
    assert ok is True
    mock_submit.assert_called_once()
    assert mock_submit.call_args[0][0] == "camp"


@patch("app.services.project_applications.submit_project_application")
def test_analytics_ruza_lead_type(mock_submit):
    mock_submit.return_value = MagicMock(notification_status="sent")
    notify_service_lead_from_analytics(
        "ruza_lead",
        {"parent_name": "Мария", "phone": "+7 916 222 33 44", "page_url": "/ruza"},
        phone="+7 916 222 33 44",
    )
    assert mock_submit.call_args[0][0] == "ruza_camp"


@patch("app.routes.shop.notify_new_application")
@patch("app.routes.shop.save_product_lead")
def test_product_lead_regression_still_notifies(mock_save, mock_notify, client):
    mock_save.return_value = MagicMock(lead_id="prod_lead_test", status="new", sheet_name="Product_Leads")
    resp = client.post(
        "/shop/api/product-request",
        json={
            "name": "Buyer",
            "phone": "+7 916 333 44 55",
            "product_id": "balance-board",
            "product_title": "Баланс-борд",
            "quantity": 1,
        },
    )
    assert resp.status_code == 200
    mock_notify.assert_called_once()
    assert mock_notify.call_args[0][0] == "product"


def test_booking_health_smoke_untouched(client):
    resp = client.get("/health/live")
    assert resp.status_code == 200
