import json
import types


def test_concierge_validation_missing_message(app, client):
    resp = client.post('/api/concierge/message', data=json.dumps({}), content_type='application/json')
    assert resp.status_code == 400
    data = resp.get_json()
    assert data.get('error') == 'message required'


def test_concierge_rate_limit_exceeded(monkeypatch, app, client):
    # Ensure limiter will deny the first request
    class DenyLimiter:
        def allow(self, key):
            return False

    monkeypatch.setitem(app.config, 'AI_GATEWAY_ENABLE_RATE_LIMIT', True)
    # monkeypatch get_limiter to return DenyLimiter
    import app.ai.security as sec
    monkeypatch.setattr(sec, '_limiter', DenyLimiter())

    payload = {'message': 'hi', 'user_id': 'u1'}
    resp = client.post('/api/concierge/message', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 429
    data = resp.get_json()
    assert data.get('error') == 'rate_limit_exceeded'
