from flask import Blueprint, request, jsonify, current_app
import logging

from app.ai.core_gateway import create_default_gateway
from app.services.google_sheets_analytics import log_analytics_event

safari_concierge_bp = Blueprint("safari_concierge", __name__, url_prefix="/api/ai/safari")
logger = logging.getLogger(__name__)


@safari_concierge_bp.route("/chat", methods=["POST"])
def safari_chat():
    """Специализированный чат-консьерж по WakeSurf Safari (маршруты, пакеты, логистика)."""
    if not current_app.config.get("ENABLE_AI_GATEWAY", True):
        return jsonify({"error": "ai_gateway_disabled"}), 503

    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    user_key = data.get("user_key") or (request.remote_addr or "anon")

    if not message:
        return jsonify({"error": "empty_message"}), 400

    gateway = create_default_gateway(current_app)
    reply = gateway.handle_message(
        user_id=user_key,
        message=message,
        context={"agent": "safari_concierge"},
    )

    # Лог в единую таблицу аналитики (sanitized)
    try:
        log_analytics_event(
            {
                "event": "safari_concierge_message",
                "context": "safari_chat",
                "user_key": user_key,
                "type": "ai_chat",
                "meta": {
                    "message": message[:200],  # preview без PII
                    "reply_type": reply.get("type"),
                },
                "ip": request.remote_addr or "",
                "user_agent": request.headers.get("User-Agent", ""),
            }
        )
    except Exception as e:
        logger.warning("[Safari concierge] analytics logging failed: %s", e)

    return jsonify(reply)


