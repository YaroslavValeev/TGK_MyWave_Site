import os
import importlib

import pytest

pytestmark = pytest.mark.skip(
    reason="Legacy API: create_default_gateway(app) and ToolDefinition removed"
)


def test_real_client_tool_call_routes_to_registered_tool(monkeypatch, client, app):
    pass
