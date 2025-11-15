"""JSON schemas and helpers for validating AI tool payloads."""
from __future__ import annotations

from typing import Dict, Any

from jsonschema import validate as jsonschema_validate

SCHEMAS: Dict[str, Dict[str, Any]] = {
    'get_services': {
        'type': 'object',
        'properties': {
<<<<<<< HEAD
            'city': {'type': ['string', 'null']},
            'tags': {
                'type': 'array',
                'items': {'type': 'string'},
=======
            'city': {
                'type': ['string', 'null'],
                'maxLength': 128,
            },
            'tags': {
                'type': 'array',
                'items': {'type': 'string', 'minLength': 1, 'maxLength': 64},
                'maxItems': 10,
                'uniqueItems': True,
>>>>>>> 3e973344234bff0b63fbd50177f122551ecd140d
            },
        },
        'additionalProperties': False,
    },
    'get_available_slots': {
        'type': 'object',
        'properties': {
<<<<<<< HEAD
            'service_id': {'type': 'string'},
=======
            'service_id': {'type': 'string', 'minLength': 1, 'maxLength': 64},
>>>>>>> 3e973344234bff0b63fbd50177f122551ecd140d
            'date': {'type': 'string', 'format': 'date'},
        },
        'required': ['service_id', 'date'],
        'additionalProperties': False,
    },
    'create_booking': {
        'type': 'object',
        'properties': {
<<<<<<< HEAD
            'service_id': {'type': 'string'},
            'date': {'type': 'string', 'format': 'date'},
            'slot': {'type': 'string'},
            'name': {'type': 'string'},
            'phone': {'type': 'string'},
            'email': {'type': ['string', 'null'], 'format': 'email'},
        },
        'required': ['service_id', 'date', 'slot', 'name', 'phone'],
=======
            'name': {'type': 'string', 'minLength': 2, 'maxLength': 128},
            'phone': {'type': 'string', 'minLength': 5, 'maxLength': 32},
            'service_id': {'type': 'string', 'minLength': 1, 'maxLength': 64},
            'slot': {
                'type': 'object',
                'properties': {
                    'date': {'type': 'string', 'format': 'date'},
                    'time': {'type': 'string', 'pattern': '^\\d{2}:\\d{2}$'},
                },
                'required': ['date', 'time'],
                'additionalProperties': False,
            },
        },
        'required': ['name', 'phone', 'service_id', 'slot'],
>>>>>>> 3e973344234bff0b63fbd50177f122551ecd140d
        'additionalProperties': False,
    },
    'get_faq_answer': {
        'type': 'object',
        'properties': {
<<<<<<< HEAD
            'question': {'type': 'string'},
=======
            'question': {'type': 'string', 'minLength': 3, 'maxLength': 512},
>>>>>>> 3e973344234bff0b63fbd50177f122551ecd140d
        },
        'required': ['question'],
        'additionalProperties': False,
    },
}


def get_schema_for(tool_name: str) -> Dict[str, Any] | None:
    """Return schema for a tool name if known."""
    return SCHEMAS.get(tool_name)


<<<<<<< HEAD
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
=======
def validate_tool_input(tool_name: str, payload: Dict[str, Any] | None) -> Dict[str, Any] | None:
    """Validate payload using the schema mapped to the tool name."""
    schema = SCHEMAS.get(tool_name)
    if not schema:
        return payload
    jsonschema_validate(instance=payload or {}, schema=schema)
    return payload
>>>>>>> 3e973344234bff0b63fbd50177f122551ecd140d
