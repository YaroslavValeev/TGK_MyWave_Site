"""Social Admin UI MVP — routes and sanitization."""

from unittest.mock import MagicMock

import pytest

from app.services.social_admin import (
    list_social_applications,
    sanitize_application_for_admin,
)


SAMPLE_APP = {
    "application_id": "soc_app_e7be01a15ded4365",
    "created_at": "2026-06-28T10:00:00Z",
    "updated_at": "2026-06-28T10:00:00Z",
    "status": "new",
    "parent_name": "Иван Иванов",
    "parent_phone": "+7 916 000 00 00",
    "child_first_name": "Алексей",
    "child_age": "12",
    "city": "Москва",
    "preferred_contact": "phone",
    "health_notes": "секретная аллергия",
    "motivation_text": "хочу на вейк",
    "source": "web_social_form",
}


def _sheet_reader(records):
    def reader(_sid, _name):
        return records

    return reader


class TestSanitizeApplicationForAdmin:
    def test_hides_health_and_motivation(self):
        safe = sanitize_application_for_admin(SAMPLE_APP)
        assert "health_notes" not in safe
        assert "motivation_text" not in safe
        assert "секретная" not in str(safe.values())
        assert safe["has_safety_info"] == "yes"

    def test_keeps_operational_fields(self):
        safe = sanitize_application_for_admin(SAMPLE_APP)
        assert safe["application_id"] == SAMPLE_APP["application_id"]
        assert safe["parent_name"] == "Иван Иванов"


class TestListSocialApplications:
    def test_status_filter(self):
        rows = list_social_applications(
            status_filter="new",
            sheet_records=_sheet_reader([SAMPLE_APP, {**SAMPLE_APP, "application_id": "soc_app_other0000001", "status": "scheduled"}]),
        )
        assert len(rows) == 1
        assert rows[0]["application_id"] == SAMPLE_APP["application_id"]


@pytest.fixture
def social_flags_on(monkeypatch):
    monkeypatch.setenv("SOCIAL_MODULE_ENABLED", "1")
    monkeypatch.setenv("SOCIAL_BOOKING_ENABLED", "1")
    monkeypatch.setenv("SPREADSHEET_ID", "test-sheet-id")


@pytest.fixture
def admin_logged_in(client, app, mocker):
    user = MagicMock()
    user.is_authenticated = True
    user.is_admin = True
    user.username = "social_admin"
    user.get_id.return_value = "99"

    mocker.patch("flask_login.utils._get_user", return_value=user)

    with client.session_transaction() as sess:
        sess["_user_id"] = "99"
        sess["_fresh"] = True
    return client


class TestAdminSocialRoutes:
    def test_list_requires_login(self, client, social_flags_on):
        resp = client.get("/admin/social/")
        assert resp.status_code in (302, 401, 403, 500)

    def test_list_503_when_booking_off(self, admin_logged_in, monkeypatch):
        monkeypatch.setenv("SOCIAL_BOOKING_ENABLED", "0")
        resp = admin_logged_in.get("/admin/social/")
        assert resp.status_code == 503

    def test_list_renders_applications(self, admin_logged_in, mocker, social_flags_on):
        mocker.patch(
            "app.routes.admin.social.list_social_applications",
            return_value=[sanitize_application_for_admin(SAMPLE_APP)],
        )
        resp = admin_logged_in.get("/admin/social/")
        assert resp.status_code == 200
        assert b"soc_app_e7be01a15ded4365" in resp.data
        assert b"\xd1\x81\xd0\xb5\xd0\xba\xd1\x80\xd0\xb5\xd1\x82" not in resp.data  # "секрет"

    def test_detail_no_health_in_body(self, admin_logged_in, mocker, social_flags_on):
        mocker.patch(
            "app.routes.admin.social.get_social_application",
            return_value=sanitize_application_for_admin(SAMPLE_APP),
        )
        mocker.patch("app.routes.admin.social.list_audit_events_for_application", return_value=[])
        resp = admin_logged_in.get(f"/admin/social/{SAMPLE_APP['application_id']}")
        assert resp.status_code == 200
        assert b"health_notes" not in resp.data
        assert b"\xd1\x81\xd0\xb5\xd0\xba\xd1\x80\xd0\xb5\xd1\x82" not in resp.data  # секрет

    def test_assign_success(self, admin_logged_in, mocker, social_flags_on):
        mocker.patch(
            "app.routes.admin.social.get_social_application",
            return_value=sanitize_application_for_admin(SAMPLE_APP),
        )
        mock_assign = mocker.patch("app.routes.admin.social.manual_assign_social_session")
        mock_assign.return_value = MagicMock(
            session_id="soc_sess_test123456789",
            application_id=SAMPLE_APP["application_id"],
            status="scheduled",
            session_date="2026-07-15",
            session_time="10:00",
            location="Зал",
        )
        mocker.patch(
            "app.routes.admin.social.is_social_admin_notifications_enabled",
            return_value=False,
        )
        resp = admin_logged_in.post(
            f"/admin/social/{SAMPLE_APP['application_id']}/assign",
            data={
                "session_date": "2026-07-15",
                "session_time": "10:00",
                "location": "Зал MyWave",
                "coach": "Coach",
                "service_type": "wake",
                "notes": "internal",
                "confirm": "yes",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
        mock_assign.assert_called_once()

    def test_assign_requires_confirm(self, admin_logged_in, mocker, social_flags_on):
        mocker.patch(
            "app.routes.admin.social.get_social_application",
            return_value=sanitize_application_for_admin(SAMPLE_APP),
        )
        resp = admin_logged_in.post(
            f"/admin/social/{SAMPLE_APP['application_id']}/assign",
            data={
                "session_date": "2026-07-15",
                "session_time": "10:00",
                "location": "Зал",
            },
        )
        assert resp.status_code == 200
        assert b"\xd0\x9f\xd0\xbe\xd0\xb4\xd1\x82\xd0\xb2\xd0\xb5\xd1\x80\xd0\xb4\xd0\xb8\xd1\x82\xd0\xb5" in resp.data  # Подтвердите
