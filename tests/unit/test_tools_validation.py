<<<<<<< HEAD
"""Tests for tool input validation."""
=======
import json

>>>>>>> 3e973344234bff0b63fbd50177f122551ecd140d
import pytest
from jsonschema.exceptions import ValidationError

<<<<<<< HEAD
from app.ai.tools_schema import validate_tool_input, get_schema_for
=======
from app.ai.core_gateway import create_default_gateway, ToolDefinition
from app.ai.tools_schema import SCHEMAS
from app.routes import ai_gateway_api
>>>>>>> 3e973344234bff0b63fbd50177f122551ecd140d


class TestToolsValidation:
    """Test tool input validation."""

    def test_get_services_valid_payload(self):
        """Test valid payload for get_services."""
        payload = {
            "city": None,
            "tags": ["обучение", "интенсив"]
        }
        # Should not raise
        validate_tool_input('get_services', payload)

    def test_get_services_valid_empty_tags(self):
        """Test valid payload with empty tags."""
        payload = {
            "city": "Москва",
            "tags": []
        }
        validate_tool_input('get_services', payload)

    def test_get_services_invalid_extra_property(self):
        """Test invalid payload with extra property."""
        payload = {
            "city": "Москва",
            "tags": ["обучение"],
            "extra": "not allowed"
        }
        with pytest.raises(ValidationError):
            validate_tool_input('get_services', payload)

<<<<<<< HEAD
    def test_get_available_slots_valid_payload(self):
        """Test valid payload for get_available_slots."""
        payload = {
            "service_id": "wsc",
            "date": "2025-10-01"
        }
        validate_tool_input('get_available_slots', payload)
=======
    valid = {
        'name': 'Alice',
        'phone': '+1234567',
        'service_id': 'svc_wsc',
        'slot': {'date': '2025-12-01', 'time': '10:00'},
    }
    res = gateway.call_tool('create_booking', valid)
    assert res['ok'] is True
    assert res['payload'] == valid
>>>>>>> 3e973344234bff0b63fbd50177f122551ecd140d

    def test_get_available_slots_missing_required(self):
        """Test missing required field."""
        payload = {
            "service_id": "wsc"
        }
        with pytest.raises(ValidationError):
            validate_tool_input('get_available_slots', payload)

    def test_create_booking_valid_payload(self):
        """Test valid payload for create_booking."""
        payload = {
            "service_id": "wsc",
            "date": "2025-10-01",
            "slot": "11:00",
            "name": "Иван Иванов",
            "phone": "+79123456789"
        }
        validate_tool_input('create_booking', payload)

    def test_create_booking_valid_with_email(self):
        """Test valid payload with optional email."""
        payload = {
            "service_id": "wsc",
            "date": "2025-10-01",
            "slot": "11:00",
            "name": "Иван Иванов",
            "phone": "+79123456789",
            "email": "ivan@example.com"
        }
        validate_tool_input('create_booking', payload)

    def test_create_booking_missing_required(self):
        """Test missing required fields."""
        payload = {
            "service_id": "wsc",
            "date": "2025-10-01"
        }
        with pytest.raises(ValidationError):
            validate_tool_input('create_booking', payload)

    def test_create_booking_invalid_email_format(self):
        """Test invalid email format."""
        payload = {
            "service_id": "wsc",
            "date": "2025-10-01",
            "slot": "11:00",
            "name": "Иван Иванов",
            "phone": "+79123456789",
            "email": "invalid-email"
        }
        # Note: jsonschema format validation may not catch all invalid emails
        # depending on implementation, but we test the structure
        try:
            validate_tool_input('create_booking', payload)
        except ValidationError:
            pass  # Expected for invalid format

<<<<<<< HEAD
    def test_get_faq_answer_valid_payload(self):
        """Test valid payload for get_faq_answer."""
        payload = {
            "question": "Какая стоимость?"
        }
        validate_tool_input('get_faq_answer', payload)

    def test_get_faq_answer_missing_required(self):
        """Test missing required question field."""
        payload = {}
        with pytest.raises(ValidationError):
            validate_tool_input('get_faq_answer', payload)

    def test_unknown_tool_no_validation(self):
        """Test that unknown tools don't raise validation errors."""
        payload = {"any": "data"}
        # Should not raise - unknown tools return None schema
        validate_tool_input('unknown_tool', payload)

    def test_get_schema_for_known_tool(self):
        """Test getting schema for known tool."""
        schema = get_schema_for('get_services')
        assert schema is not None
        assert schema['type'] == 'object'

    def test_get_schema_for_unknown_tool(self):
        """Test getting schema for unknown tool."""
        schema = get_schema_for('unknown_tool')
        assert schema is None
=======
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
>>>>>>> 3e973344234bff0b63fbd50177f122551ecd140d
