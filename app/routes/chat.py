from app.services.openai import get_chat_response
from flask import Blueprint, jsonify, request, current_app
from flask_wtf.csrf import CSRFProtect

bp = Blueprint('chat', __name__)
csrf = CSRFProtect()
csrf.exempt(bp)  # Отключаем CSRF для этого blueprint для теста

@bp.route("/chat", methods=["POST"])
def chat_handler():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Ошибка: нет данных"}), 400
        if "message" not in data or not isinstance(data["message"], str):
            return jsonify({"error": "Ошибка: поле 'message' обязательно"}), 400
        reply = get_chat_response(data["message"])
        return jsonify({"reply": reply})
    except Exception as e:
        current_app.logger.error(f"Chat error: {str(e)}")
        return jsonify({"error": f"Ошибка сервера: {str(e)}"}), 500
