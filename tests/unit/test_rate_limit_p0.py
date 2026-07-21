"""P0 rate-limit regression tests (no global 200/day cap)."""

from __future__ import annotations

import pytest

from app.config.rate_limit_config import RateLimitConfig
from app.services.rate_limit import get_client_ip, is_public_unlimited_request


@pytest.fixture
def rl_client(app):
    app.config["RATELIMIT_DEFAULT_LIMITS"] = []
    app.config["RATELIMIT_AUTH_LOGIN"] = "3 per minute"
    app.config["RATELIMIT_BOOKING_CREATE"] = "2 per minute"
    return app.test_client()


def test_default_limits_empty_no_hardcoded_global_cap():
    assert RateLimitConfig.DEFAULT_LIMITS == tuple()
    assert "200 per day" not in str(RateLimitConfig.DEFAULT_LIMITS)
    assert "50 per hour" not in str(RateLimitConfig.DEFAULT_LIMITS)


def test_public_get_requests_not_unlimited_for_post(app):
    with app.test_request_context("/api/calendar/book", method="POST"):
        assert is_public_unlimited_request() is False


def test_public_health_get_is_unlimited(app):
    with app.test_request_context("/health", method="GET"):
        assert is_public_unlimited_request() is True
    with app.test_request_context("/api/health/live", method="GET"):
        assert is_public_unlimited_request() is True


def test_many_public_gets_never_429(rl_client):
    for _ in range(220):
        resp = rl_client.get("/health/live")
        assert resp.status_code == 200
        assert resp.status_code != 429


def test_health_never_blocked(rl_client):
    for _ in range(300):
        resp = rl_client.get("/health")
        assert resp.status_code in (200, 503)
        assert resp.status_code != 429


def test_login_endpoint_rate_limited(rl_client):
    payload = {"email": "user@example.com", "password": "password"}
    statuses = []
    for _ in range(8):
        resp = rl_client.post("/api/auth/login", json=payload)
        statuses.append(resp.status_code)
    assert 429 in statuses


def test_login_429_json_retry_after(rl_client):
    payload = {"email": "user@example.com", "password": "password"}
    last = None
    for _ in range(10):
        last = rl_client.post(
            "/api/auth/login",
            json=payload,
            headers={"Accept": "application/json"},
        )
        if last.status_code == 429:
            break
    assert last is not None
    assert last.status_code == 429
    assert last.headers.get("Retry-After")
    body = last.get_json()
    assert body.get("error") == "rate_limit_exceeded"
    assert body.get("retry_after")


def test_different_client_ips_have_separate_counters(rl_client, monkeypatch):
    class _FakeQuery:
        def filter_by(self, **_kwargs):
            return self

        def first(self):
            return None

    monkeypatch.setattr("app.routes.api.User", type("User", (), {"query": _FakeQuery()}))

    payload = {"email": "user@example.com", "password": "password"}
    ip_a = "198.51.100.10"
    ip_b = "203.0.113.20"
    for _ in range(6):
        resp = rl_client.post(
            "/api/auth/login",
            json=payload,
            environ_base={"REMOTE_ADDR": ip_a},
        )
        assert resp.status_code in (400, 401, 404, 429)
    blocked = rl_client.post(
        "/api/auth/login",
        json=payload,
        environ_base={"REMOTE_ADDR": ip_a},
    )
    assert blocked.status_code == 429

    fresh = rl_client.post(
        "/api/auth/login",
        json=payload,
        environ_base={"REMOTE_ADDR": ip_b},
    )
    assert fresh.status_code != 429


def test_booking_create_abuse_limited(rl_client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.calendar_routes._book_slot_internal",
        lambda: (__import__("flask").jsonify({"status": "ok"}), 200),
    )
    payload = {"date": "2026-08-01", "time": "10:00", "name": "Test", "phone": "+79990000000"}
    statuses = []
    for _ in range(12):
        resp = rl_client.post("/api/calendar/book", json=payload)
        statuses.append(resp.status_code)
    assert 429 in statuses


def test_get_client_ip_uses_x_forwarded_for(app):
    apply = __import__("app.services.rate_limit", fromlist=["apply_proxy_fix"]).apply_proxy_fix
    apply(app)
    with app.test_request_context(
        "/",
        headers={"X-Forwarded-For": "203.0.113.55, 10.0.0.1"},
        environ_base={"REMOTE_ADDR": "127.0.0.1"},
    ):
        assert get_client_ip() == "203.0.113.55"


def test_static_path_skipped_by_public_filter(app):
    with app.test_request_context("/static/js/booking.js", method="GET"):
        assert is_public_unlimited_request() is True
