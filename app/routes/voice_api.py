from flask import Blueprint, request, jsonify, current_app
import logging

from app.ai.core_gateway import create_default_gateway
from app.services.openai_service import transcribe_audio
from app.services.google_sheets_analytics import log_analytics_event

voice_bp = Blueprint("voice", __name__, url_prefix="/api/voice")
logger = logging.getLogger(__name__)


@voice_bp.route("/transcribe_and_reply", methods=["POST"])
def transcribe_and_reply():
    if not current_app.config.get("ENABLE_VOICE"):
        return jsonify({"error": "voice_disabled"}), 503

    if "file" not in request.files:
        return jsonify({"error": "file_required"}), 400

    audio = request.files["file"]
    user_key = request.form.get("user_key") or (request.remote_addr or "anon")

    try:
        transcript = transcribe_audio(audio)
    except Exception as e:
        logger.exception("[VOICE] transcribe error: %s", e)
        return jsonify({"error": "transcribe_error"}), 500

    gateway = create_default_gateway(current_app)
    reply = gateway.handle_message(
        user_id=user_key,
        message=transcript,
        context={"agent": "voice_assistant"},
    )

    # Аналитика
    try:
        log_analytics_event(
            {
                "event": "voice_message",
                "context": "voice_api",
                "user_key": user_key,
                "type": "ai_chat",
                "meta": {
                    "transcript_preview": transcript[:200],
                    "reply_type": reply.get("type"),
                },
                "ip": request.remote_addr or "",
                "user_agent": request.headers.get("User-Agent", ""),
            }
        )
    except Exception as e:
        logger.warning("[Voice] analytics logging failed: %s", e)

    return jsonify({"transcript": transcript, "reply": reply})


