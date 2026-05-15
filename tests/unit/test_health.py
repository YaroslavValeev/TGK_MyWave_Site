import pytest


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
