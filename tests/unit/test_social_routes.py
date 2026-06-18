"""Social Mission public routes (Social-2/4 staging UI)."""

import pytest


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
    monkeypatch.setenv("SOCIAL_PUBLIC_STATS_ENABLED", "1")


class TestSocialRoutesGating:
    def test_social_page_404_when_module_off(self, client):
        rv = client.get("/social")
        assert rv.status_code == 404

    def test_social_page_200_when_module_on(self, client, social_flags_on):
        rv = client.get("/social")
        assert rv.status_code == 200
        assert "Социальная миссия" in rv.get_data(as_text=True)

    def test_home_widget_hidden_when_flags_off(self, client, mocker):
        mocker.patch("app.services.competitions.store.get_ticker_items", return_value=[])
        mocker.patch("app.services.blog.store.get_posts", return_value=([], 0))
        html = client.get("/").get_data(as_text=True)
        assert "social-mission-widget" not in html

    def test_home_widget_visible_when_enabled(self, client, social_flags_on, mocker):
        mocker.patch("app.services.competitions.store.get_ticker_items", return_value=[])
        mocker.patch("app.services.blog.store.get_posts", return_value=([], 0))
        html = client.get("/").get_data(as_text=True)
        assert "social-mission-widget" in html
        assert "social-mission-widget--compact" in html
        assert "Каждый сет помогает движению" in html
        assert "Подробнее" in html


class TestSocialApplyApi:
    def test_apply_503_when_disabled(self, client, social_flags_on, monkeypatch):
        monkeypatch.setenv("SOCIAL_APPLICATIONS_ENABLED", "0")
        rv = client.post("/api/social/apply", json=_valid_payload())
        assert rv.status_code == 503

    def test_apply_rejects_forbidden_booking_fields(self, client, social_flags_on):
        payload = _valid_payload(date="2026-07-01", slot="10:00", booking_id="b1")
        rv = client.post("/api/social/apply", json=payload)
        assert rv.status_code == 400
        body = rv.get_json()
        assert body["ok"] is False

    def test_apply_valid_payload_with_consent_version(self, client, social_flags_on, mocker):
        from app.services.social_store import SocialWriteResult

        mocker.patch(
            "app.routes.social.append_social_application",
            return_value=SocialWriteResult(
                application_id="soc_app_consent",
                status="new",
                sheet_name="Social_Applications",
            ),
        )
        rv = client.post("/api/social/apply", json=_valid_payload(consent_version="2026-06-v1"))
        assert rv.status_code == 201
        assert rv.get_json()["ok"] is True

    def test_apply_missing_consent_version_returns_400(self, client, social_flags_on):
        payload = _valid_payload()
        del payload["consent_version"]
        rv = client.post("/api/social/apply", json=payload)
        assert rv.status_code == 400
        body = rv.get_json()
        assert body["ok"] is False
        assert "required:consent_version" in body["errors"]

    def test_social_form_renders_consent_version_hidden_field(self, client, social_flags_on):
        html = client.get("/social").get_data(as_text=True)
        assert 'name="consent_version"' in html
        assert 'value="2026-06-v1"' in html

    def test_apply_success_mock_sheet(self, client, social_flags_on, mocker):
        from app.services.social_store import SocialWriteResult

        captured = {}

        def fake_append(data, **kwargs):
            captured["data"] = dict(data)
            return SocialWriteResult(
                application_id="soc_app_test",
                status="new",
                sheet_name="Social_Applications",
            )

        mocker.patch("app.routes.social.append_social_application", side_effect=fake_append)
        rv = client.post("/api/social/apply", json=_valid_payload())
        assert rv.status_code == 201
        assert rv.get_json()["application_id"] == "soc_app_test"
        assert "booking_id" not in captured["data"]

    def test_apply_does_not_call_booking_api(self, client, social_flags_on, mocker):
        from app.services.social_store import SocialWriteResult

        booking_spy = mocker.patch("app.routes.api.real_book_slot")
        mocker.patch(
            "app.routes.social.append_social_application",
            return_value=SocialWriteResult(
                application_id="soc_app_x",
                status="new",
                sheet_name="Social_Applications",
            ),
        )
        client.post("/api/social/apply", json=_valid_payload())
        booking_spy.assert_not_called()
