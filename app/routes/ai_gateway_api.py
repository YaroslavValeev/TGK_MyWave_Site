from flask import Blueprint, request, jsonify
from app.ai.core_gateway import create_default_gateway, ToolDefinition
from app.ai.security import require_ai_api_key
from app.ai.metrics import REQUEST_COUNTER, TOOL_CALL_COUNTER, TOOL_RESULT_COUNTER, LATENCY_HISTOGRAM
import time

# Blueprint has no internal prefix; the application will mount it under
# /api/ai/gateway when registering in app.create_app
ai_gateway_bp = Blueprint('ai_gateway', __name__)

# create a default gateway instance (mock by default)
gateway = create_default_gateway()


@ai_gateway_bp.route('/message', methods=['POST'])
@require_ai_api_key
def message():
    data = request.get_json() or {}
    user_message = data.get('message')
    user_id = data.get('user_id')
    if not user_message:
        return jsonify({'error': 'message required'}), 400

    # Instrumentation: count request and measure latency
    REQUEST_COUNTER.inc()
    start = time.time()
    resp = gateway.handle_message(user_message, user_id=user_id)
    latency = time.time() - start
    try:
        LATENCY_HISTOGRAM.observe(latency)
    except Exception:
        pass

    # If model asked for tool calls, increment tool call counter (observability)
    if isinstance(resp, dict) and resp.get('type') == 'tool_result':
        TOOL_RESULT_COUNTER.inc()
    return jsonify(resp)


# Simple admin endpoint to register a test tool at runtime (useful for dev/tests)
@ai_gateway_bp.route('/tools/register_test', methods=['POST'])
@require_ai_api_key
def register_test_tool():
    data = request.get_json() or {}
    name = data.get('name') or 'echo'

    def echo_tool(payload: dict):
        return {'echo': payload}

    tool = ToolDefinition(name=name, description='dev-registered echo tool')
    try:
        gateway.register_tool(tool, echo_tool)
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'ok': True, 'tool': name})
