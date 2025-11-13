import pytest


def test_health_endpoint_structure(client):
    resp = client.get('/api/health')
    assert resp.status_code in (200, 503)
    data = resp.get_json()
    assert 'status' in data
    assert 'checks' in data
    checks = data['checks']
    # Basic expected keys
    assert 'version' in checks
    assert 'mode' in checks
    assert 'database' in checks
    assert 'cache' in checks
    assert 'ai_gateway' in checks
