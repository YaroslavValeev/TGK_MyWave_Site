import pytest
from unittest.mock import patch


@pytest.mark.parametrize("path", ["/health", "/api/health"])
def test_health_endpoint_structure(client, path):
    resp = client.get(path)
    assert resp.status_code in (200, 503)
    data = resp.get_json()
    assert "status" in data
    assert "checks" in data
    checks = data["checks"]
    assert "version" in checks
    assert "mode" in checks
    assert "database" in checks
    assert "cache" in checks
    assert "redis" in checks
    assert "google" in checks
    assert "ai_gateway" in checks


def test_health_live_always_ok(client):
    for path in ("/health/live", "/api/health/live"):
        resp = client.get(path)
        assert resp.status_code == 200
        assert resp.get_json().get("live") is True


def test_health_degraded_not_503_when_db_ok(client):
    resp = client.get("/health")
    if resp.status_code == 200:
        assert resp.get_json()["status"] in ("ok", "degraded")


@pytest.mark.parametrize("path", ["/health/ready", "/api/health/ready"])
def test_health_ready_ok_when_db_ok_and_optional_skipped(client, path):
    """Readiness ignores skipped optional checks (Sentry, AI gateway, etc.)."""
    with patch("app.routes.health._check_database", return_value={"ok": True, "critical": True}), patch(
        "app.routes.health._check_sentry",
        return_value={"ok": True, "optional": True, "skipped": True, "error": "SENTRY_DSN not configured"},
    ), patch(
        "app.routes.health._check_ai_gateway",
        return_value={"ok": True, "optional": True, "skipped": True, "error": "ai health check disabled"},
    ), patch(
        "app.routes.health._check_redis",
        return_value={"ok": True, "optional": True, "skipped": True, "error": "REDIS_URL not configured"},
    ), patch(
        "app.routes.health._check_google",
        return_value={"ok": True, "optional": True, "skipped": True, "error": "credentials path not set"},
    ), patch(
        "app.routes.health._check_cache",
        return_value={"ok": True, "optional": True},
    ):
        resp = client.get(path)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["checks"]["sentry"]["skipped"] is True
    assert data["checks"]["ai_gateway"]["skipped"] is True


@pytest.mark.parametrize("path", ["/health/ready", "/api/health/ready"])
def test_health_ready_unhealthy_when_database_fails(client, path):
    with patch(
        "app.routes.health._check_database",
        return_value={"ok": False, "critical": True, "error": "db down"},
    ), patch("app.routes.health._check_sentry", return_value={"ok": True, "optional": True, "skipped": True}), patch(
        "app.routes.health._check_ai_gateway",
        return_value={"ok": True, "optional": True, "skipped": True},
    ), patch("app.routes.health._check_redis", return_value={"ok": True, "optional": True, "skipped": True}), patch(
        "app.routes.health._check_google",
        return_value={"ok": True, "optional": True, "skipped": True},
    ), patch("app.routes.health._check_cache", return_value={"ok": True, "optional": True}):
        resp = client.get(path)
    assert resp.status_code == 503
    assert resp.get_json()["status"] == "unhealthy"


def test_health_ready_not_degraded_when_configured_optional_fails(client):
    """Configured optional failure must not affect readiness."""
    with patch("app.routes.health._check_database", return_value={"ok": True, "critical": True}), patch(
        "app.routes.health._check_redis",
        return_value={"ok": False, "optional": True, "configured": True, "error": "connection refused"},
    ), patch("app.routes.health._check_sentry", return_value={"ok": True, "optional": True, "skipped": True}), patch(
        "app.routes.health._check_ai_gateway",
        return_value={"ok": True, "optional": True, "skipped": True},
    ), patch("app.routes.health._check_google", return_value={"ok": True, "optional": True, "skipped": True}), patch(
        "app.routes.health._check_cache",
        return_value={"ok": True, "optional": True},
    ):
        resp = client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_health_shows_optional_skipped_in_payload(client):
    with patch("app.routes.health._check_database", return_value={"ok": True, "critical": True}), patch(
        "app.routes.health._check_sentry",
        return_value={
            "ok": True,
            "optional": True,
            "skipped": True,
            "configured": False,
            "error": "SENTRY_DSN not configured",
        },
    ), patch(
        "app.routes.health._check_ai_gateway",
        return_value={"ok": True, "optional": True, "skipped": True, "error": "ai health check disabled"},
    ), patch("app.routes.health._check_redis", return_value={"ok": True, "optional": True, "skipped": True}), patch(
        "app.routes.health._check_google",
        return_value={"ok": True, "optional": True, "skipped": True},
    ), patch("app.routes.health._check_cache", return_value={"ok": True, "optional": True}):
        resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["checks"]["sentry"]["skipped"] is True
    assert data["checks"]["ai_gateway"]["skipped"] is True


def test_health_degraded_when_configured_optional_fails(client):
    with patch("app.routes.health._check_database", return_value={"ok": True, "critical": True}), patch(
        "app.routes.health._check_redis",
        return_value={"ok": False, "optional": True, "configured": True, "error": "connection refused"},
    ), patch("app.routes.health._check_sentry", return_value={"ok": True, "optional": True, "skipped": True}), patch(
        "app.routes.health._check_ai_gateway",
        return_value={"ok": True, "optional": True, "skipped": True},
    ), patch("app.routes.health._check_google", return_value={"ok": True, "optional": True, "skipped": True}), patch(
        "app.routes.health._check_cache",
        return_value={"ok": True, "optional": True},
    ):
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "degraded"


def test_sentry_unconfigured_returns_skipped(app):
    from app.routes.health import _check_sentry

    with app.app_context():
        with patch.dict("os.environ", {}, clear=True):
            app.config["SENTRY_DSN"] = None
            result = _check_sentry()
    assert result["skipped"] is True
    assert result["optional"] is True
    assert result["ok"] is True


def test_ai_gateway_disabled_returns_skipped(app):
    from app.routes.health import _check_ai_gateway

    with app.app_context():
        with patch.dict("os.environ", {}, clear=True):
            app.config["ENABLE_AI_HEALTH_CHECK"] = None
            result = _check_ai_gateway()
    assert result["skipped"] is True
    assert result["optional"] is True
    assert result["ok"] is True
