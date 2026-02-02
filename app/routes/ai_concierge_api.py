"""AI Concierge HTTP API for Site MyWave."""

from __future__ import annotations

from flask import Blueprint, jsonify, request, current_app

from app.ai.core_gateway import create_default_gateway
from app.ai.metrics import CONCIERGE_REQUEST_COUNTER
from app.ai.security import get_limiter

ai_concierge_bp = Blueprint("ai_concierge", __name__)

_gateway = None


def get_gateway():
    global _gateway
    if _gateway is None:
        _gateway = create_default_gateway(current_app)
    return _gateway


def _clean_str(value):
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed:
            return trimmed
    return None


@ai_concierge_bp.route("/message", methods=["POST"])
def concierge_message():
    data = request.get_json(silent=True) or {}
    message = _clean_str(data.get("message"))
    user_id = _clean_str(data.get("user_id"))

    if not message:
        return jsonify({"error": "message required"}), 400
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    page = _clean_str(data.get("page"))
    lang = _clean_str(data.get("lang")) or "ru"
    context = {"page": page, "lang": lang}

    try:
        CONCIERGE_REQUEST_COUNTER.inc()
    except Exception:
        # Metrics should never break request handling.
        pass

    # Optional rate limiting leverages the same limiter helper as the legacy concierge API.
    try:
        if current_app.config.get("AI_GATEWAY_ENABLE_RATE_LIMIT"):
            limiter = get_limiter()
            bucket = user_id or request.remote_addr or "anon"
            if not limiter.allow(bucket):
                return jsonify({"error": "rate_limit_exceeded"}), 429
    except Exception:
        current_app.logger.exception(
            "Concierge rate limit check failed; allowing request"
        )

    try:
        resp = get_gateway().handle_message(message, user_id=user_id, context=context)
    except Exception as exc:
        current_app.logger.exception("Concierge gateway failure")
        return jsonify({"error": "gateway_error", "details": str(exc)}), 502

    return jsonify({"reply": resp})
