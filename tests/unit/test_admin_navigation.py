"""Admin navigation — no silent redirects to dashboard."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def admin_logged_in(client, app, mocker):
    user = MagicMock()
    user.is_authenticated = True
    user.is_admin = True
    user.username = "nav_admin"
    user.email = "nav_admin@example.com"
    user.get_id.return_value = "42"
    mocker.patch("flask_login.utils._get_user", return_value=user)
    with client.session_transaction() as sess:
        sess["_user_id"] = "42"
        sess["_fresh"] = True
    return client


class TestAdminNavigation:
    def test_admin_dashboard_has_distinct_nav_targets(self, admin_logged_in):
        resp = admin_logged_in.get("/admin/")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert 'href="/admin/"' in body or "href='/admin/'" in body
        assert "/admin/social/" in body
        assert "/admin/images/" in body
        assert "/admin/blog" in body
        assert "/admin/events" in body
        assert "/admin/users" in body
        assert "/admin/settings" in body

    def test_admin_sections_return_200_with_content(self, admin_logged_in):
        cases = {
            "/admin/blog": ("Публикации", "Блог"),
            "/admin/events": ("Календарные события", "События"),
            "/admin/users": ("Пользователи Site", "Пользователи"),
            "/admin/settings": ("Статус модулей", "Настройки"),
        }
        for path, needles in cases.items():
            resp = admin_logged_in.get(path)
            assert resp.status_code == 200
            body = resp.get_data(as_text=True)
            assert "Раздел готовится" not in body
            for needle in needles:
                assert needle in body

    def test_admin_shell_has_no_public_chat_marker(self, admin_logged_in):
        resp = admin_logged_in.get("/admin/")
        body = resp.get_data(as_text=True)
        assert "admin-sidebar" in body
        assert "admin.css" in body
        assert "site-header" not in body
