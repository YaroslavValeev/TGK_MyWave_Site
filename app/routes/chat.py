from flask import Blueprint, request, jsonify
from app.services.ai_router import smart_gpt_response

chat_bp = Blueprint("chat", __name__)

@chat_bp.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message")
        client_id = request.remote_addr  # или любой другой способ идентификации

        if not user_message:
            return jsonify({"error": "Пустое сообщение"}), 400

        # Отправляем сообщение в универсальный обработчик (без голосовых функций)
        reply = smart_gpt_response(user_message, client_id=client_id, source="web")
        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": f"Ошибка обработки: {str(e)}"}), 500
