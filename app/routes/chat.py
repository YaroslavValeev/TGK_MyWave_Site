from app.services.openai import get_chat_response
from flask import Blueprint, jsonify, request, current_app, render_template
from flask_wtf.csrf import CSRFProtect
from app.models import ChatMessage

bp = Blueprint('chat', __name__, template_folder='../templates')
csrf = CSRFProtect()
csrf.exempt(bp)  # Отключаем CSRF для этого blueprint

@bp.route("/")
def chat():
    messages = ChatMessage.query.order_by(ChatMessage.created_at.asc()).all()
    return render_template("chat.html", messages=messages)

@bp.route("/api", methods=["POST"])
def chat_handler():
    try:
        message = request.json.get('message')
        if not message:
            return jsonify({'error': 'No message provided'}), 400

        # 👤 Идентификатор пользователя для контекста чата
        client_id = request.headers.get("X-User-Id") or request.remote_addr

        response = get_chat_response(message, client_id=client_id)
        return jsonify({'response': response})
    except Exception as e:
        current_app.logger.error(f"OpenAI API error: {str(e)}")
        return jsonify({
            'response': 'Извините, произошла ошибка при обработке вашего сообщения.'
        }), 500
