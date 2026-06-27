"""PR56 boot / env-flag regression — no import-time side effects."""

from unittest.mock import patch

import pytest


@pytest.fixture
def fresh_app(monkeypatch):
    """Minimal app boot with controlled env."""
    monkeypatch.setenv("ENABLE_GOOGLE_SERVICES", "0")
    monkeypatch.setenv("SOCIAL_MODULE_ENABLED", "1")
    from app import create_app

    return create_app("testing")


class TestPR56ImportSafety:
    def test_import_social_sessions_no_side_effects(self):
        import app.services.social_sessions as mod

        assert hasattr(mod, "manual_assign_social_session")
        assert hasattr(mod, "transition_social_session_status")

    def test_main_import_booking_flag_off(self, monkeypatch):
        monkeypatch.setenv("SOCIAL_BOOKING_ENABLED", "0")
        monkeypatch.setenv("ENABLE_GOOGLE_SERVICES", "0")
        import importlib

        import main

        importlib.reload(main)
        assert main.app is not None

    def test_main_import_booking_flag_on_no_admin_token(self, monkeypatch):
        monkeypatch.delenv("ADMIN_TOKEN", raising=False)
        monkeypatch.setenv("SOCIAL_BOOKING_ENABLED", "1")
        monkeypatch.setenv("SOCIAL_MODULE_ENABLED", "1")
        monkeypatch.setenv("ENABLE_GOOGLE_SERVICES", "0")
        import importlib

        import main

        importlib.reload(main)
        assert main.app is not None


class TestPR56RouteGating:
    def test_assign_503_when_booking_disabled(self, client, monkeypatch):
        monkeypatch.setenv("SOCIAL_MODULE_ENABLED", "1")
        monkeypatch.setenv("SOCIAL_BOOKING_ENABLED", "0")
        resp = client.post(
            "/api/social/sessions/assign",
            json={
                "application_id": "soc_app_aaaaaaaaaaaaaaaa",
                "session_date": "2026-07-01",
                "session_time": "10:00",
                "assigned_by": "admin",
            },
        )
        assert resp.status_code == 503

    def test_assign_401_when_token_required(self, client, monkeypatch):
        monkeypatch.setenv("SOCIAL_MODULE_ENABLED", "1")
        monkeypatch.setenv("SOCIAL_BOOKING_ENABLED", "1")
        monkeypatch.setitem(client.application.config, "ADMIN_TOKEN", "secret-token")
        resp = client.post(
            "/api/social/sessions/assign",
            json={
                "application_id": "soc_app_aaaaaaaaaaaaaaaa",
                "session_date": "2026-07-01",
                "session_time": "10:00",
                "assigned_by": "admin",
            },
        )
        assert resp.status_code == 401

    def test_status_503_when_booking_disabled(self, client, monkeypatch):
        monkeypatch.setenv("SOCIAL_MODULE_ENABLED", "1")
        monkeypatch.setenv("SOCIAL_BOOKING_ENABLED", "0")
        resp = client.post(
            "/api/social/sessions/soc_sess_1111111111111111/status",
            json={"status": "completed"},
        )
        assert resp.status_code == 503

    def test_public_apply_does_not_call_assign(self, client, monkeypatch):
        monkeypatch.setenv("SOCIAL_MODULE_ENABLED", "1")
        monkeypatch.setenv("SOCIAL_APPLICATIONS_ENABLED", "1")
        monkeypatch.setenv("SOCIAL_BOOKING_ENABLED", "1")
        payload = {
            "parent_name": "Test",
            "parent_phone": "+7 916 000 00 00",
            "child_first_name": "Child",
            "child_age": 12,
            "preferred_contact": "phone",
            "consent_personal_data": True,
            "consent_training": True,
            "consent_version": "2026-06-v1",
        }
        with patch("app.routes.social.append_social_application") as mock_append:
            mock_append.return_value = type(
                "R", (), {"application_id": "soc_app_x", "status": "new"}
            )()
            with patch("app.routes.social.manual_assign_social_session") as mock_assign:
                with patch("app.routes.social.notify_new_application"):
                    client.post("/api/social/apply", json=payload)
        mock_assign.assert_not_called()
