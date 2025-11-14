import json

from app.routes import ai_concierge_api


def test_concierge_requires_message_and_user(client):
    resp = client.post('/api/concierge/message', json={'user_id': 'u1'})
    assert resp.status_code == 400
    resp = client.post('/api/concierge/message', json={'message': 'hello'})
    assert resp.status_code == 400
    resp = client.post('/api/concierge/message', json={'message': '', 'user_id': '  '})
    assert resp.status_code == 400


def test_concierge_valid_flow(monkeypatch, client):
    class DummyGateway:
        def __init__(self):
            self.calls = []

        def handle_message(self, message, user_id=None, context=None):
            self.calls.append({'message': message, 'user_id': user_id, 'context': context})
            return {'type': 'assistant', 'text': f"hi {user_id}", 'context': context}

    dummy = DummyGateway()
    monkeypatch.setattr(ai_concierge_api, 'gateway', dummy)

    payload = {
        'message': 'Need help',
        'user_id': 'user-42',
        'page': 'landing',
        'lang': 'en',
    }
    resp = client.post('/api/concierge/message', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['reply']['type'] == 'assistant'
    assert dummy.calls[0]['context'] == {'page': 'landing', 'lang': 'en'}
