import time
import pytest

from app import create_app


def test_default_allows_requests_without_key(client, app):
    # By default in testing mode, AI_GATEWAY_REQUIRE_API_KEY should be False
    app.config["AI_GATEWAY_REQUIRE_API_KEY"] = False
    resp = client.post("/api/ai/gateway/message", json={"message": "hello"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    assert data.get("type") == "assistant"


def test_api_key_enforced_and_validated(client, app):
    # Enable API key requirement and set allowed keys
    app.config["AI_GATEWAY_REQUIRE_API_KEY"] = True
    app.config["AI_GATEWAY_API_KEYS"] = ["goodkey"]

    # Missing key -> 401
    r = client.post("/api/ai/gateway/message", json={"message": "hi"})
    assert r.status_code == 401

    # Wrong key -> 401
    r = client.post(
        "/api/ai/gateway/message",
        json={"message": "hi"},
        headers={"Authorization": "Bearer badkey"},
    )
    assert r.status_code == 401

    # Correct key -> 200
    r = client.post(
        "/api/ai/gateway/message",
        json={"message": "hi"},
        headers={"Authorization": "Bearer goodkey"},
    )
    assert r.status_code == 200
    assert r.get_json().get("type") == "assistant"


def test_rate_limit_exceeded(client, app):
    # Ensure limiter is reset between tests for deterministic behavior
    import importlib

    sec = importlib.import_module("app.ai.security")
    # reset internal limiter
    try:
        sec._limiter = None
    except Exception:
        pass

    app.config["AI_GATEWAY_REQUIRE_API_KEY"] = True
    app.config["AI_GATEWAY_API_KEYS"] = ["rlkey"]
    app.config["AI_GATEWAY_ENABLE_RATE_LIMIT"] = True
    app.config["AI_GATEWAY_RATE_LIMIT_COUNT"] = 2
    app.config["AI_GATEWAY_RATE_LIMIT_WINDOW"] = 60

    headers = {"Authorization": "Bearer rlkey"}

    r1 = client.post("/api/ai/gateway/message", json={"message": "m1"}, headers=headers)
    assert r1.status_code == 200
    r2 = client.post("/api/ai/gateway/message", json={"message": "m2"}, headers=headers)
    assert r2.status_code == 200
    # third should be rate-limited
    r3 = client.post("/api/ai/gateway/message", json={"message": "m3"}, headers=headers)
    assert r3.status_code == 429
    j = r3.get_json() or {}
    assert j.get("error") == "rate_limit_exceeded"
