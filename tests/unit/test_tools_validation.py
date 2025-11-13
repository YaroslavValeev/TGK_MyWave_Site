import pytest

from app.ai.core_gateway import create_default_gateway, ToolDefinition
from app.ai.tools_schema import SCHEMAS


def test_tool_registration_and_valid_payload():
    gateway = create_default_gateway()

    schema = SCHEMAS['create_booking']

    def echo_tool(payload):
        return {'ok': True, 'payload': payload}

    gateway.register_tool(ToolDefinition(name='create_booking', description='test', schema=schema), echo_tool)

    valid = {'date': '2025-12-01', 'time': '10:00', 'name': 'Alice', 'phone': '+123'}
    res = gateway.call_tool('create_booking', valid)
    assert res['ok'] is True
    assert res['payload'] == valid


def test_tool_registration_and_invalid_payload_raises():
    gateway = create_default_gateway()

    schema = SCHEMAS['create_booking']

    def echo_tool(payload):
        return {'ok': True}

    gateway.register_tool(ToolDefinition(name='create_booking', description='test', schema=schema), echo_tool)

    invalid = {'date': '2025-12-01', 'name': 'Alice'}  # missing required time and phone
    import jsonschema

    with pytest.raises(jsonschema.exceptions.ValidationError):
        gateway.call_tool('create_booking', invalid)
