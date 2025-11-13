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
            'slug': {'type': 'string'},
        },
        'additionalProperties': False,
    },
    'get_available_slots': {
        'type': 'object',
        'properties': {
            'date': {'type': 'string', 'format': 'date'},
        },
        'required': ['date'],
        'additionalProperties': False,
    },
    'create_booking': {
        'type': 'object',
        'properties': {
            'date': {'type': 'string', 'format': 'date'},
            'time': {'type': 'string'},
            'name': {'type': 'string'},
            'phone': {'type': 'string'},
            'email': {'type': 'string', 'format': 'email'},
        },
        'required': ['date', 'time', 'name', 'phone'],
        'additionalProperties': False,
    },
}


def get_schema_for(tool_name: str) -> Dict[str, Any]:
    """Return schema for a tool name or None if not known."""
    return SCHEMAS.get(tool_name)
