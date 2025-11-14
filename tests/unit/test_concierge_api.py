import json


def test_concierge_message_endpoint(app, client):
    # Use default MYWAVE_AI_MODE=mock behavior
    payload = {'message': 'Hello concierge', 'user_id': 'test-user'}
    resp = client.post('/api/concierge/message', data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'reply' in data
    assert isinstance(data['reply'], dict)
    # mock client should return assistant type
    assert data['reply'].get('type') in ('assistant',)
