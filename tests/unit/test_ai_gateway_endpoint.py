import json


def test_ai_gateway_message_endpoint(client):
    # simple assistant message
    resp = client.post('/api/ai/gateway/message', json={'message': 'hello api'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('type') == 'assistant'


def test_ai_gateway_register_tool_and_call(client):
    # Register a test echo tool
    r = client.post('/api/ai/gateway/tools/register_test', json={'name': 'echo_test'})
    assert r.status_code == 200
    # Trigger tool via special mock message format
    call_msg = '__call_tool__:echo_test:' + json.dumps({'a': 1})
    resp = client.post('/api/ai/gateway/message', json={'message': call_msg})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('type') in ('tool_result', 'tool_error')
