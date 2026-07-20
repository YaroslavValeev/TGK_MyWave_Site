"""Integration tests for /camps public routes."""

import pytest

from app.config import camp_features
from app.services.camps.showcase import ShowcaseDetailResult, ShowcaseListResult
from tests.unit.test_camp_showcase import MVP_CAMP


@pytest.fixture
def camp_public_enabled(monkeypatch):
    monkeypatch.setenv("CAMP_MODULE_ENABLED", "1")
    monkeypatch.setenv("CAMP_PUBLIC_ENABLED", "1")
    monkeypatch.setattr(camp_features, "is_camp_module_enabled", lambda: True)
    monkeypatch.setattr(camp_features, "is_camp_public_enabled", lambda: True)


def test_camps_index_404_when_disabled(client):
    response = client.get("/camps")
    assert response.status_code == 404


def test_camps_index_lists_mvp_camp(client, camp_public_enabled, mocker):
    mocker.patch(
        "app.routes.camps.fetch_showcase_camps",
        return_value=ShowcaseListResult(state="ok", camps=[{"id": MVP_CAMP["id"], "title": MVP_CAMP["title"]}]),
    )
    response = client.get("/camps")
    assert response.status_code == 200
    assert MVP_CAMP["id"] in response.get_data(as_text=True)
    assert "Кемпы" not in response.get_data(as_text=True) or "MVP Wakesurf Camp" in response.get_data(as_text=True)


def test_camps_index_api_error_not_empty_state(client, camp_public_enabled, mocker):
    mocker.patch(
        "app.routes.camps.fetch_showcase_camps",
        return_value=ShowcaseListResult(state="error_auth", message="auth failed"),
    )
    response = client.get("/camps")
    assert response.status_code == 502
    body = response.get_data(as_text=True)
    assert "временно недоступен" in body.lower()
    assert "Пока пусто" not in body


def test_camps_detail_ok(client, camp_public_enabled, mocker):
    mocker.patch(
        "app.routes.camps.fetch_showcase_detail",
        return_value=ShowcaseDetailResult(
            state="ok",
            camp={
                "id": MVP_CAMP["id"],
                "title": MVP_CAMP["title"],
                "partnership_confirmed": False,
                "source_badge": "Из MyWaveTour",
                "availability_label": "Есть места",
            },
        ),
    )
    response = client.get(f"/camps/{MVP_CAMP['id']}")
    assert response.status_code == 200
    assert MVP_CAMP["title"] in response.get_data(as_text=True)


def test_camps_detail_not_found(client, camp_public_enabled, mocker):
    mocker.patch(
        "app.routes.camps.fetch_showcase_detail",
        return_value=ShowcaseDetailResult(state="not_found", message="missing"),
    )
    response = client.get("/camps/missing-id")
    assert response.status_code == 404


def test_camps_token_not_exposed_in_html(client, camp_public_enabled, mocker):
    secret = "super-secret-camp-token-value"
    mocker.patch(
        "app.routes.camps.fetch_showcase_camps",
        return_value=ShowcaseListResult(state="ok", camps=[{"id": MVP_CAMP["id"], "title": MVP_CAMP["title"]}]),
    )
    mocker.patch("app.config.camp_features.mywave_tour_camp_api_token", return_value=secret)
    response = client.get("/camps")
    assert secret not in response.get_data(as_text=True)


def test_nav_contains_camps_link(client, camp_public_enabled, mocker):
    mocker.patch(
        "app.routes.camps.fetch_showcase_camps",
        return_value=ShowcaseListResult(state="empty", camps=[]),
    )
    response = client.get("/camps")
    assert response.status_code == 200
    assert 'href="/camps"' in response.get_data(as_text=True) or "Кемпы" in response.get_data(as_text=True)


def test_projects_camp_redirects_to_camps(client, camp_public_enabled):
    response = client.get("/projects/camp", follow_redirects=False)
    assert response.status_code == 301
    assert "/camps" in response.headers["Location"]
