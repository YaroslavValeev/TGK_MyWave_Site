from flask import Blueprint, request, jsonify
from app.services.openai_service import ask
from app.services.rules import ChatMode

ai_router_bp = Blueprint("ai_router", __name__)


@ai_router_bp.route("/ai/message", methods=["POST"])
def route_message():
    data = request.get_json() or {}
    prompt = data.get("prompt")
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400
    # Выбор режима из query-параметра, по умолчанию RESPONSES_API
    mode_str = request.args.get("mode", "RESPONSES_API")
    try:
        mode = ChatMode[mode_str]
    except KeyError:
        return jsonify({"error": f"Unknown mode: {mode_str}"}), 400
    response = ask(prompt, mode=mode)
    return jsonify({"response": response, "mode": mode.value})
