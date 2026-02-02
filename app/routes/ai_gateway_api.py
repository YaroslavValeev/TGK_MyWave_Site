from flask import Blueprint, request, jsonify, current_app
from app.ai.core_gateway import create_default_gateway
from app.ai.security import require_ai_api_key
from app.ai.metrics import (
    REQUEST_COUNTER,
    TOOL_CALL_COUNTER,
    TOOL_RESULT_COUNTER,
    LATENCY_HISTOGRAM,
)
import time

# Blueprint has no internal prefix; the application will mount it under
# /api/ai/gateway when registering in app.create_app
ai_gateway_bp = Blueprint("ai_gateway", __name__)

_gateway = None


def get_gateway():
    global _gateway
    if _gateway is None:
        _gateway = create_default_gateway(current_app)
    return _gateway


@ai_gateway_bp.route("/message", methods=["POST"])
@require_ai_api_key
def message():
    data = request.get_json() or {}
    user_message = data.get("message")
    user_id = data.get("user_id")
    if not user_message:
        return jsonify({"error": "message required"}), 400

    # Instrumentation: count request and measure latency
    REQUEST_COUNTER.inc()
    start = time.time()
    resp = get_gateway().handle_message(user_message, user_id=user_id)
    latency = time.time() - start
    try:
        LATENCY_HISTOGRAM.observe(latency)
    except Exception:
        pass

    # If model asked for tool calls, increment tool call counter (observability)
    status_code = 200
    if isinstance(resp, dict):
        if resp.get("type") == "tool_result":
            TOOL_RESULT_COUNTER.inc()
        elif resp.get("type") == "error":
            status_code = 400
    return jsonify(resp), status_code


# Simple admin endpoint to register a test tool at runtime (useful for dev/tests)
@ai_gateway_bp.route("/tools/register_test", methods=["POST"])
@require_ai_api_key
def register_test_tool():
    data = request.get_json() or {}
    name = data.get("name") or "echo"

    def echo_tool(payload: dict):
        return {"echo": payload}

    try:
        get_gateway().register_tool(name, echo_tool)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True, "tool": name})
