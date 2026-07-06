"""Online Coaching HTTP route smoke tests."""

import os

import pytest

from app.services.online_coaching_store import validate_application_payload


@pytest.fixture()
def oc_client(monkeypatch):
    monkeypatch.setenv("ONLINE_COACHING_ENABLED", "1")
    monkeypatch.setenv("ONLINE_COACHING_APPLICATIONS_ENABLED", "1")
    monkeypatch.setenv("ONLINE_COACHING_ADMIN_ENABLED", "1")
    monkeypatch.setenv("ONLINE_COACHING_NOTIFICATIONS_ENABLED", "0")
    monkeypatch.setenv("DISABLE_TELEGRAM", "1")

    from app import create_app

    app = create_app("development")
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        yield client


def test_online_coaching_page_ok(oc_client):
    resp = oc_client.get("/services/online-coaching")
    assert resp.status_code == 200
    assert b"Online Coaching" in resp.data or b"\xd0\x9e\xd0\xbd\xd0\xbb\xd0\xb0\xd0\xb9\xd0\xbd" in resp.data


def test_online_coaching_short_redirect(oc_client):
    resp = oc_client.get("/online-coaching", follow_redirects=False)
    assert resp.status_code == 302
    assert "/services/online-coaching" in resp.headers.get("Location", "")


def test_apply_validation_errors(oc_client):
    resp = oc_client.post("/api/online-coaching/apply", json={})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data.get("ok") is False
    assert data.get("errors")


def test_apply_disabled_when_flag_off(monkeypatch):
    monkeypatch.setenv("ONLINE_COACHING_ENABLED", "1")
    monkeypatch.setenv("ONLINE_COACHING_APPLICATIONS_ENABLED", "0")
    monkeypatch.setenv("DISABLE_TELEGRAM", "1")

    from app import create_app

    app = create_app("development")
    app.config["TESTING"] = True
    with app.test_client() as client:
        resp = client.post(
            "/api/online-coaching/apply",
            json={
                "name": "Test",
                "phone": "+79161234567",
                "service_type": "video_check",
                "preferred_channel": "phone",
                "consent_personal_data": True,
                "consent_version": "2026-07-v1",
            },
        )
    assert resp.status_code == 503


def test_validate_application_payload_happy_path():
    errors = validate_application_payload(
        {
            "name": "Ivan",
            "phone": "+7 916 123-45-67",
            "service_type": "video_check",
            "preferred_channel": "telegram",
            "telegram_username": "@ivan",
            "consent_personal_data": True,
            "consent_version": "2026-07-v1",
        }
    )
    assert errors == []


def test_module_hidden_when_disabled(monkeypatch):
    monkeypatch.setenv("ONLINE_COACHING_ENABLED", "0")
    monkeypatch.setenv("DISABLE_TELEGRAM", "1")

    from app import create_app

    app = create_app("development")
    app.config["TESTING"] = True
    with app.test_client() as client:
        resp = client.get("/services/online-coaching")
    assert resp.status_code == 404
