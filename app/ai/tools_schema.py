"""JSON schemas and helpers for validating AI tool payloads."""
from __future__ import annotations

from typing import Dict, Any

from jsonschema import validate as jsonschema_validate

SCHEMAS: Dict[str, Dict[str, Any]] = {
    'get_services': {
        'type': 'object',
        'properties': {
            'city': {
                'type': ['string', 'null'],
                'maxLength': 128,
            },
            'tags': {
                'type': 'array',
                'items': {'type': 'string', 'minLength': 1, 'maxLength': 64},
                'maxItems': 10,
                'uniqueItems': True,
            },
        },
        'additionalProperties': False,
    },
    'get_available_slots': {
        'type': 'object',
        'properties': {
            'service_id': {'type': 'string', 'minLength': 1, 'maxLength': 64},
            'date': {'type': 'string', 'format': 'date'},
        },
        'required': ['service_id', 'date'],
        'additionalProperties': False,
    },
    'create_booking': {
        'type': 'object',
        'properties': {
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
        'additionalProperties': False,
    },
    'get_faq_answer': {
        'type': 'object',
        'properties': {
            'question': {'type': 'string', 'minLength': 3, 'maxLength': 512},
        },
        'required': ['question'],
        'additionalProperties': False,
    },
}


def get_schema_for(tool_name: str) -> Dict[str, Any] | None:
    """Return schema for a tool name if known."""
    return SCHEMAS.get(tool_name)


def validate_tool_input(tool_name: str, payload: Dict[str, Any] | None) -> Dict[str, Any] | None:
    """Validate payload using the schema mapped to the tool name."""
    schema = SCHEMAS.get(tool_name)
    if not schema:
        return payload
    jsonschema_validate(instance=payload or {}, schema=schema)
    return payload
