from __future__ import annotations

from typing import Dict, Any, Callable, Optional
import json
import logging

from flask import current_app

logger = logging.getLogger(__name__)

ToolFn = Callable[[Dict[str, Any]], Any]


class MCPRegistry:
    """Простой реестр MCP / external-tools для AI Gateway."""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolFn] = {}

    def register(self, name: str, fn: ToolFn) -> None:
        if not name or not callable(fn):
            raise ValueError("Invalid MCP tool registration")
        logger.info("[MCP] register tool=%s", name)
        self._tools[name] = fn

    def get(self, name: str) -> Optional[ToolFn]:
        return self._tools.get(name)

    def all_names(self) -> list[str]:
        return list(self._tools.keys())


mcp_registry = MCPRegistry()


def load_mcp_tools_from_config() -> Dict[str, Any]:
    """
    Загружает JSON-описание MCP-tools из MCP_TOOLS_JSON (путь к файлу).
    Используется как справочник схем для OpenAI tools.
    """
    cfg_path = current_app.config.get("MCP_TOOLS_JSON")
    if not cfg_path:
        logger.info("[MCP] MCP_TOOLS_JSON not set, skip loading")
        return {}
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        tools_count = len((data or {}).get("tools", []) or [])
        logger.info("[MCP] Loaded %s tools from %s", tools_count, cfg_path)
        return data or {}
    except Exception as e:
        logger.error("[MCP] Failed to load MCP tools JSON: %s", e)
        return {}
