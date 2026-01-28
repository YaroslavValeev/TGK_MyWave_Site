from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional
import logging

from flask import Flask

from app.ai.mcp_registry import mcp_registry, load_mcp_tools_from_config
from app.ai.register_tools import register_all_tools
from app.services.openai_service import ask
from app.services.rules import ChatMode

logger = logging.getLogger(__name__)


ToolFn = Callable[[Dict[str, Any]], Any]


@dataclass
class AIGateway:
    """
    Minimal AI gateway skeleton:
    - holds a tool registry
    - provides a single handle_message entrypoint

    Tool execution loop / function-calling can be added later; for now this is a stable façade.
    """

    app: Flask
    tools: Dict[str, ToolFn]

    def register_tool(self, name: str, fn: ToolFn) -> None:
        if not name or not callable(fn):
            raise ValueError("Invalid tool registration")
        self.tools[name] = fn

    def handle_message(self, user_id: str, message: str, context: Optional[dict] = None) -> Dict[str, Any]:
        # Keep it deterministic and safe: no logging of raw message/user PII
        try:
            text = ask(message, mode=ChatMode.RESPONSES_API, client_id=user_id, source=(context or {}).get("agent", "web"))
            return {"type": "text", "text": text}
        except Exception as e:
            logger.error("[AI gateway] handle_message error: %s", e)
            return {"type": "error", "error": "ai_unavailable"}


def create_default_gateway(app: Flask) -> AIGateway:
    gateway = AIGateway(app=app, tools={})

    # Register built-in tools (if present)
    try:
        register_all_tools(gateway)
    except Exception as e:
        logger.error("[AI gateway] failed to register tools: %s", e)

    # === MCP tools wiring (optional) ===
    try:
        if app.config.get("ENABLE_MCP"):
            _ = load_mcp_tools_from_config()
            logger.info("[MCP] Enabled with tools: %s", mcp_registry.all_names())
    except Exception as e:
        logger.error("[MCP] Failed to init MCP layer: %s", e)

    return gateway


