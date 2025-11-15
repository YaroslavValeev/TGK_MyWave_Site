"""JSON schemas for AI function-calling tools and helpers for validation.

Keep schemas small and explicit. They are used by the CoreAIGateway to validate
tool input before invoking adapters.
"""
from typing import Dict, Any

# Minimal schemas for the default tools registered in register_tools.py
SCHEMAS: Dict[str, Dict[str, Any]] = {
    'get_services': {
        'type': 'object',
        'properties': {
            'city': {'type': ['string', 'null']},
            'tags': {
                'type': 'array',
                'items': {'type': 'string'},
            },
        },
        'additionalProperties': False,
    },
    'get_available_slots': {
        'type': 'object',
        'properties': {
            'service_id': {'type': 'string'},
            'date': {'type': 'string', 'format': 'date'},
        },
        'required': ['service_id', 'date'],
        'additionalProperties': False,
    },
    'create_booking': {
        'type': 'object',
        'properties': {
            'service_id': {'type': 'string'},
            'date': {'type': 'string', 'format': 'date'},
            'slot': {'type': 'string'},
            'name': {'type': 'string'},
            'phone': {'type': 'string'},
            'email': {'type': ['string', 'null'], 'format': 'email'},
        },
        'required': ['service_id', 'date', 'slot', 'name', 'phone'],
        'additionalProperties': False,
    },
    'get_faq_answer': {
        'type': 'object',
        'properties': {
            'question': {'type': 'string'},
        },
        'required': ['question'],
        'additionalProperties': False,
    },
}


def get_schema_for(tool_name: str) -> Dict[str, Any]:
    """Return schema for a tool name or None if not known."""
    return SCHEMAS.get(tool_name)


def validate_tool_input(tool_name: str, payload: Dict[str, Any]) -> None:
    """Validate tool input payload against its schema.

    Raises jsonschema.ValidationError if validation fails.
    """
    schema = get_schema_for(tool_name)
    if not schema:
        # If no schema defined, skip validation (backward compatibility)
        return

    try:
        from jsonschema import validate
        validate(instance=payload or {}, schema=schema)
    except ImportError:
        # If jsonschema is not available, skip validation
        pass
