import json

import pytest

from app.ai.core_gateway import create_default_gateway, ToolDefinition
from app.ai.tools_schema import SCHEMAS
from app.routes import ai_gateway_api


def test_tool_registration_and_valid_payload():
    gateway = create_default_gateway()

    schema = SCHEMAS['create_booking']

    def echo_tool(payload):
        return {'ok': True, 'payload': payload}

    gateway.register_tool(ToolDefinition(name='create_booking', description='test', schema=schema), echo_tool)

    valid = {
        'name': 'Alice',
        'phone': '+1234567',
        'service_id': 'svc_wsc',
        'slot': {'date': '2025-12-01', 'time': '10:00'},
    }
    res = gateway.call_tool('create_booking', valid)
    assert res['ok'] is True
    assert res['payload'] == valid


def test_tool_registration_and_invalid_payload_raises():
    gateway = create_default_gateway()

    schema = SCHEMAS['create_booking']

    def echo_tool(payload):
        return {'ok': True}

    gateway.register_tool(ToolDefinition(name='create_booking', description='test', schema=schema), echo_tool)

    invalid = {'name': 'Alice', 'phone': '+123'}  # missing service_id and slot
    import jsonschema

    with pytest.raises(jsonschema.exceptions.ValidationError):
        gateway.call_tool('create_booking', invalid)


@pytest.fixture
def reset_gateway(monkeypatch):
    gateway = create_default_gateway()
    monkeypatch.setattr(ai_gateway_api, 'gateway', gateway)
    return gateway


def _register_booking_tool(gateway):
    schema = SCHEMAS['create_booking']

    def echo_tool(payload):
        return {'ok': True, 'payload': payload}

    gateway.register_tool(ToolDefinition(name='create_booking', description='test', schema=schema), echo_tool)


def test_gateway_valid_payload_returns_ok(client, reset_gateway):
    gateway = reset_gateway
    _register_booking_tool(gateway)

    payload = {
        'name': 'Alice',
        'phone': '+1234567',
        'service_id': 'svc_1',
        'slot': {'date': '2025-12-01', 'time': '09:30'},
    }
    message = '__call_tool__:create_booking:' + json.dumps(payload)

    resp = client.post('/api/ai/gateway/message', json={'message': message})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['type'] == 'tool_result'
    assert data['tool'] == 'create_booking'


def test_gateway_invalid_payload_returns_400(client, reset_gateway):
    gateway = reset_gateway
    _register_booking_tool(gateway)

    invalid_payload = {
        'name': 'Alice',
        'phone': '+1234567',
        # missing service_id and slot
    }
    message = '__call_tool__:create_booking:' + json.dumps(invalid_payload)

    resp = client.post('/api/ai/gateway/message', json={'message': message})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data == {'type': 'error', 'error': 'invalid_payload'}
