import os
import importlib

import pytest


def test_real_client_tool_call_routes_to_registered_tool(monkeypatch, client, app):
    # Ensure factory will create a real client
    monkeypatch.setenv('MYWAVE_AI_MODE', 'real')

    # Reload module to pick up env var change
    import app.ai.core_gateway as cg
    importlib.reload(cg)

    # Mock respond_structured to request a tool call
    def fake_respond(prompt, state=None, tools=None):
        return {'tool_calls': [{'name': 'test_tool', 'arguments': {'a': 1}}]}

    monkeypatch.setattr('app.services.openai_service.respond_structured', fake_respond)

    # Create gateway using factory
    gw = cg.create_default_gateway()

    # Register a tool
    def tfn(payload):
        return {'ok': True, 'payload': payload}

    from app.ai.core_gateway import ToolDefinition
    gw.register_tool(ToolDefinition('test_tool', 'desc'), tfn)

    # Send a message that will trigger respond_structured -> tool_call
    out = gw.handle_message('please call tool', user_id='u1')
    assert out.get('type') == 'tool_result'
    assert out.get('tool') == 'test_tool'
    assert out.get('result', {}).get('ok') is True
