"""Admin access control — login_required + admin_required."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def social_flags_on(monkeypatch):
    monkeypatch.setenv("SOCIAL_MODULE_ENABLED", "1")
    monkeypatch.setenv("SOCIAL_BOOKING_ENABLED", "1")
    monkeypatch.setenv("SPREADSHEET_ID", "test-sheet-id")


def _session_login(client, user_id: str):
    with client.session_transaction() as sess:
        sess["_user_id"] = user_id
        sess["_fresh"] = True


@pytest.fixture
def admin_logged_in(client, mocker):
    user = MagicMock()
    user.is_authenticated = True
    user.is_admin = True
    user.username = "access_admin"
    user.email = "access_admin@example.com"
    user.get_id.return_value = "99"
    mocker.patch("flask_login.utils._get_user", return_value=user)
    _session_login(client, "99")
    return client


class TestAdminAccessControl:
    @pytest.mark.parametrize(
        "path",
        [
            "/admin/",
            "/admin/images/",
            "/admin/social/",
            "/admin/blog",
            "/admin/settings",
        ],
    )
    def test_unauthenticated_redirects_to_login(self, client, path, social_flags_on):
        resp = client.get(path)
        assert resp.status_code in (302, 401, 403)
        if resp.status_code == 302:
            assert "/login" in (resp.location or "")

    def test_non_admin_denied_on_admin_index(self, client, mocker, social_flags_on):
        user = MagicMock()
        user.is_authenticated = True
        user.is_admin = False
        user.get_id.return_value = "7"
        mocker.patch("flask_login.utils._get_user", return_value=user)
        _session_login(client, "7")

        resp = client.get("/admin/")
        assert resp.status_code in (302, 403, 500)
        assert resp.status_code != 200

    def test_admin_can_access_admin_index(self, admin_logged_in, social_flags_on):
        resp = admin_logged_in.get("/admin/")
        assert resp.status_code == 200

    def test_admin_can_access_social_list(self, admin_logged_in, mocker, social_flags_on):
        mocker.patch(
            "app.routes.admin.social.list_social_applications",
            return_value=[],
        )
        resp = admin_logged_in.get("/admin/social/")
        assert resp.status_code == 200

    def test_admin_can_access_images(self, admin_logged_in, social_flags_on):
        resp = admin_logged_in.get("/admin/images/")
        assert resp.status_code == 200
