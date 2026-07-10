"""Integration tests for YCLIENTS webhook."""

from __future__ import annotations

import pytest


@pytest.fixture
def client(app):
    return app.test_client()


def test_yclients_webhook_disabled(client, monkeypatch):
    monkeypatch.setenv("YCLIENTS_ENABLED", "0")
    resp = client.post(
        "/public/integrations/yclients/webhook",
        json={"resource": {"id": "1"}},
    )
    assert resp.status_code == 503
    assert resp.get_json()["error"] == "yclients_disabled"


def test_yclients_webhook_unauthorized(client, monkeypatch):
    monkeypatch.setenv("YCLIENTS_ENABLED", "1")
    monkeypatch.setenv("YCLIENTS_WEBHOOK_SECRET", "test-secret")
    monkeypatch.setenv("YCLIENTS_PARTNER_TOKEN", "partner")
    resp = client.post(
        "/public/integrations/yclients/webhook",
        json={"resource": {"id": "99", "company_id": "2043174"}},
    )
    assert resp.status_code == 401


def test_yclients_webhook_ok_stub(client, monkeypatch):
    monkeypatch.setenv("YCLIENTS_ENABLED", "1")
    monkeypatch.setenv("YCLIENTS_WEBHOOK_SECRET", "test-secret")
    monkeypatch.setenv("YCLIENTS_PARTNER_TOKEN", "partner")
    resp = client.post(
        "/public/integrations/yclients/webhook",
        json={"resource": {"id": "99", "company_id": "2043174", "status": "confirmed"}},
        headers={"X-YCLIENTS-Webhook-Secret": "test-secret"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["result"]["status"] == "stub"
