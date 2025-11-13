"""Core AI Gateway - a lightweight, testable integration layer for OpenAI.

This module provides a small, dependency-free facade that can be used in
development (mocked) and production (real OpenAI client). It supports:
- registration of callable tools (by name)
- dispatching simple tool calls
- sending chat-like messages to the configured client

Design choices (intentional):
- keep runtime dependencies minimal so unit tests don't need OpenAI SDK
- expose a MockOpenAIClient to allow local development and CI tests
- keep function-calling plumbing simple and explicit (a real implementation
  can replace the client with one that calls OpenAI Responses / Agents SDK)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional
import json
import os


@dataclass
class ToolDefinition:
    name: str
    description: str
    schema: Optional[Dict[str, Any]] = None


class OpenAIClientInterface:
    """Minimal interface for an OpenAI-like client.

    A production client should implement `send_chat` and optionally
    `parse_function_response` if using function calling.
    """

    def send_chat(self, system: str, user_message: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError()


class MockOpenAIClient(OpenAIClientInterface):
    """Simple mock client for local testing.

    Behavior:
    - If the user message matches the pattern `__call_tool__:tool_name:payload`,
      returns a structured response indicating a tool call request.
    - Otherwise returns a trivial assistant reply.
    """

    def send_chat(self, system: str, user_message: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        # Detect fake function-calling trigger
        if user_message.startswith("__call_tool__:"):
            try:
                _, tool_name, payload = user_message.split(':', 2)
            except ValueError:
                tool_name = 'unknown'
                payload = '{}'

            # Simulate the model requesting a tool call by returning a special structure
            return {
                'type': 'tool_call',
                'tool_name': tool_name,
                'tool_payload': json.loads(payload or '{}')
            }

        # Default assistant response
        return {'type': 'assistant', 'text': f"(mock reply) I received: {user_message}"}


class CoreAIGateway:
    """Registers tools and routes messages through the OpenAI client.

    Usage pattern:
    - instantiate with a client (mock or real)
    - register tool callbacks via `register_tool(name, callable)`
    - call `handle_message(user_message, user_id)` to get a response
    """

    def __init__(self, client: OpenAIClientInterface, system_prompt: Optional[str] = None):
        self.client = client
        self.system_prompt = system_prompt or "You are a helpful assistant."
        self.tools: Dict[str, Callable[[Dict[str, Any]], Any]] = {}

    def register_tool(self, tool: ToolDefinition, fn: Callable[[Dict[str, Any]], Any]) -> None:
        if tool.name in self.tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self.tools[tool.name] = fn

    def call_tool(self, tool_name: str, payload: Dict[str, Any]) -> Any:
        fn = self.tools.get(tool_name)
        if fn is None:
            raise KeyError(f"unknown tool: {tool_name}")
        return fn(payload)

    def handle_message(self, user_message: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Send message to client and handle possible tool-call responses.

        Returns a dict with keys depending on response type:
        - assistant: {'type': 'assistant', 'text': '...'}
        - tool_result: {'type': 'tool_result', 'tool': name, 'result': ...}
        """
        resp = self.client.send_chat(self.system_prompt, user_message, user_id=user_id)

        if not isinstance(resp, dict):
            return {'type': 'assistant', 'text': str(resp)}

        if resp.get('type') == 'tool_call':
            tool_name = resp.get('tool_name')
            payload = resp.get('tool_payload') or {}
            try:
                # count tool calls for metrics if available
                try:
                    from app.ai.metrics import TOOL_CALL_COUNTER
                    TOOL_CALL_COUNTER.inc()
                except Exception:
                    pass

                result = self.call_tool(tool_name, payload)
            except Exception as exc:
                return {'type': 'tool_error', 'tool': tool_name, 'error': str(exc)}
            return {'type': 'tool_result', 'tool': tool_name, 'result': result}

        # Default passthrough
        return resp


# Helper to create a default gateway depending on env var
def create_default_gateway() -> CoreAIGateway:
    mode = os.environ.get('MYWAVE_AI_MODE', 'mock')
    if mode == 'real':
        # Production: use a real client backed by app.services.openai_service.respond_structured
        class RealOpenAIClient(OpenAIClientInterface):
            def send_chat(self, system: str, user_message: str, user_id: Optional[str] = None) -> Dict[str, Any]:
                # Import lazily to avoid circular imports at module load time
                try:
                    from app.services.openai_service import respond_structured
                except Exception as e:
                    raise RuntimeError(f'RealOpenAIClient failed to import dependencies: {e}')

                # Call the structured responder
                try:
                    data = respond_structured(user_message)
                except Exception as e:
                    return {'type': 'assistant', 'text': f'error: {e}'}

                # If the model requested tool calls, map to gateway tool_call shape
                if isinstance(data, dict) and 'tool_calls' in data and isinstance(data['tool_calls'], list) and data['tool_calls']:
                    first = data['tool_calls'][0]
                    name = first.get('name')
                    args = first.get('arguments') or {}
                    return {'type': 'tool_call', 'tool_name': name, 'tool_payload': args}

                # Otherwise return assistant structured content
                return {'type': 'assistant', 'text': str(data), 'structured': data}

        client = RealOpenAIClient()
    else:
        client = MockOpenAIClient()

    system = os.environ.get('MYWAVE_AI_SYSTEM_PROMPT', 'You are a helpful assistant for MyWave.')
    return CoreAIGateway(client=client, system_prompt=system)


__all__ = ['CoreAIGateway', 'MockOpenAIClient', 'ToolDefinition', 'create_default_gateway']
