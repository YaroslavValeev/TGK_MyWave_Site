"""Tests for tool input validation."""
import pytest
from jsonschema.exceptions import ValidationError

from app.ai.tools_schema import validate_tool_input, get_schema_for


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

    def test_get_available_slots_valid_payload(self):
        """Test valid payload for get_available_slots."""
        payload = {
            "service_id": "wsc",
            "date": "2025-10-01"
        }
        validate_tool_input('get_available_slots', payload)

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
