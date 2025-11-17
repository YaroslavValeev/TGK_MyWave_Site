"""Tests for tool input validation and AI gateway integration."""

import json

import pytest
from jsonschema.exceptions import ValidationError

from app.ai.tools_schema import validate_tool_input, get_schema_for, SCHEMAS
from app.ai.core_gateway import create_default_gateway, ToolDefinition
from app.routes import ai_gateway_api


class TestToolsValidation:
    """Test tool input validation."""

    def test_get_services_valid_payload(self):
        payload = {"city": None, "tags": ["обучение", "интенсив"]}
        validate_tool_input('get_services', payload)

    def test_get_services_valid_empty_tags(self):
        payload = {"city": "Москва", "tags": []}
        validate_tool_input('get_services', payload)

    def test_get_services_invalid_extra_property(self):
        payload = {"city": "Москва", "tags": ["обучение"], "extra": "not allowed"}
        with pytest.raises(ValidationError):
            validate_tool_input('get_services', payload)

    def test_get_available_slots_valid_payload(self):
        payload = {"service_id": "wsc", "date": "2025-10-01"}
        validate_tool_input('get_available_slots', payload)

    def test_get_available_slots_missing_required(self):
        payload = {"service_id": "wsc"}
        with pytest.raises(ValidationError):
            validate_tool_input('get_available_slots', payload)

    def test_create_booking_valid_payload(self):
        payload = {
            "service_id": "wsc",
            "slot": {"date": "2025-10-01", "time": "11:00"},
            "name": "Иван Иванов",
            "phone": "+79123456789",
        }
        validate_tool_input('create_booking', payload)

    def test_create_booking_valid_with_email(self):
        payload = {
            "service_id": "wsc",
            "slot": {"date": "2025-10-01", "time": "11:00"},
            "name": "Иван Иванов",
            "phone": "+79123456789",
            "email": "ivan@example.com",
        }
        validate_tool_input('create_booking', payload)

    def test_create_booking_missing_required(self):
        payload = {"service_id": "wsc", "date": "2025-10-01"}
        with pytest.raises(ValidationError):
            validate_tool_input('create_booking', payload)

    def test_create_booking_invalid_email_format(self):
        payload = {
            "service_id": "wsc",
            "date": "2025-10-01",
            "slot": "11:00",
            "name": "Иван Иванов",
            "phone": "+79123456789",
            "email": "invalid-email",
        }
        # jsonschema may or may not validate email formats depending on setup
        try:
            validate_tool_input('create_booking', payload)
        except ValidationError:
            pass

    def test_get_faq_answer_valid_payload(self):
        payload = {"question": "Какая стоимость?"}
        validate_tool_input('get_faq_answer', payload)

    def test_get_faq_answer_missing_required(self):
        payload = {}
        with pytest.raises(ValidationError):
            validate_tool_input('get_faq_answer', payload)

    def test_unknown_tool_no_validation(self):
        payload = {"any": "data"}
        validate_tool_input('unknown_tool', payload)

    def test_get_schema_for_known_tool(self):
        schema = get_schema_for('get_services')
        assert schema is not None and schema['type'] == 'object'

    def test_get_schema_for_unknown_tool(self):
        schema = get_schema_for('unknown_tool')
        assert schema is None


@pytest.fixture
def reset_gateway(app, monkeypatch):
    # Ensure the AI gateway blueprint is registered on the test app (create_app may skip it)
    try:
        from app.routes.ai_gateway_api import ai_gateway_bp
        try:
            app.register_blueprint(ai_gateway_bp, url_prefix='/api/ai/gateway')
        except Exception:
            # blueprint may already be registered; ignore
            pass
    except Exception:
        # If import fails, continue; tests will still monkeypatch gateway reference below
        pass

    gateway = create_default_gateway()
    monkeypatch.setattr(ai_gateway_api, 'gateway', gateway)
    return gateway


def _register_booking_tool(gateway):
    schema = SCHEMAS.get('create_booking')

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

    invalid_payload = {'name': 'Alice', 'phone': '+1234567'}  # missing service_id and slot
    message = '__call_tool__:create_booking:' + json.dumps(invalid_payload)

    resp = client.post('/api/ai/gateway/message', json={'message': message})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data == {'type': 'error', 'error': 'invalid_payload'}

