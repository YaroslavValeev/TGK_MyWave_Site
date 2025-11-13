import json


def post_message(client, message):
    return client.post('/api/ai/gateway/message', data=json.dumps({'message': message}), content_type='application/json')


def test_get_services_tool(client):
    # request tool call for get_services
    resp = post_message(client, '__call_tool__:get_services:{}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('type') == 'tool_result'
    assert data.get('tool') == 'get_services'
    result = data.get('result')
    assert isinstance(result, dict)
    assert 'projects' in result


def test_get_slots_tool(monkeypatch, client):
    # provide a fake get_available_slots implementation
    fake_slots = [{'time': '10:00', 'available': 5, 'max_capacity': 10, 'booked': 5}]
    # Override the tool implementation on the gateway directly so we don't
    # depend on the closure that was created at app init.
    from app.routes.ai_gateway_api import gateway

    def fake_get_slots_tool(payload):
        return {'date': payload.get('date'), 'slots': fake_slots}

    gateway.tools['get_available_slots'] = fake_get_slots_tool

    resp = post_message(client, '__call_tool__:get_available_slots:{"date":"2025-12-01"}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('type') == 'tool_result'
    assert data.get('tool') == 'get_available_slots'
    result = data.get('result')
    assert result.get('date') == '2025-12-01'
    assert isinstance(result.get('slots'), list)


def test_create_booking_tool(monkeypatch, client):
    # Replace the create_booking tool on the gateway to avoid Google Sheets calls
    from app.routes.ai_gateway_api import gateway

    def fake_create_booking(payload):
        # emulate book_slot return
        return {'success': True, 'confirm_text': 'http://confirm'}

    gateway.tools['create_booking'] = fake_create_booking

    payload = json.dumps({"date":"2025-12-01","time":"10:00","name":"Ivan","phone":"+70000000000"})
    resp = post_message(client, f'__call_tool__:create_booking:{payload}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('type') == 'tool_result'
    assert data.get('tool') == 'create_booking'
    result = data.get('result')
    # create_booking_tool returns the tuple result from book_slot, but register_tools wraps into result
    assert isinstance(result, dict) or isinstance(result, (list, tuple))
