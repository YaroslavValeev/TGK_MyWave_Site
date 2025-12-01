from flask import Blueprint, jsonify, request, current_app, render_template
from app.database.models import ChatMessage, db  # ChatMessage должен быть связан с db из app.database
from app.services.openai_service import ask
from app.modules.logger import log_event
from app.services.google_sheets_analytics import log_analytics_event
from openai import OpenAIError

chat_bp = Blueprint('chat', __name__, template_folder='../templates', url_prefix='/chat')

def _clean_assistant_text(text: str) -> str:
    try:
        if not text:
            return ""
        cleaned = str(text)
        # Remove helper labels like "Прямой ответ:", "Пояснение/польза:", etc.
        patterns = [
            r"Прямой\s*ответ\s*:\s*",
            r"Пояснение\s*/\s*польза\s*:\s*",
            r"Пояснение\s*:\s*",
            r"Польза\s*:\s*",
            r"Приглашение\s*:\s*",
        ]
        for pat in patterns:
            import re
            cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)
        # Remove leading bullets
        cleaned = re.sub(r"^[\-•]\s*", "", cleaned, flags=re.MULTILINE)
        # Collapse excess blank lines
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()
    except Exception:
        return text

@chat_bp.route("/")
def chat_page():
    messages = ChatMessage.query.order_by(ChatMessage.created_at.asc()).all()
    # Передаем csrf_token в шаблон
    return render_template("chat.html", messages=messages)

@chat_bp.route("/api", methods=["POST"])
def chat_handler():
    try:
        current_app.logger.info("Получен новый запрос к чату")
        data = request.get_json()
        if not data:
            current_app.logger.error("Отсутствуют данные в запросе")
            return jsonify({'error': 'Отсутствуют данные'}), 400

        message = data.get('message')
        history = data.get('history')
        if not message or not isinstance(message, str):
            current_app.logger.error(f"Некорректное сообщение: {message}")
            return jsonify({'error': 'Некорректное сообщение'}), 400

        # Идентификатор пользователя для контекста чата
        client_id = request.headers.get("X-User-Id") or request.remote_addr
        current_app.logger.info(f"Обработка сообщения от пользователя {client_id}: {message}")

        # Получаем ответ от OpenAI
        current_app.logger.info("Отправка запроса к OpenAI")
        # Передаём историю, если есть
        text_lc = (message or '').strip().lower()
        info_intent = any(kw in text_lc for kw in (
            'как ', 'что такое', 'объясни', 'поясни', 'трик', 'трюк', 'олли', '360', 'разворот', 'поворот', 'вейк'
        ))
        if info_intent:
            from app.services.responses_api import get_response_with_knowledge as _resp
            reply = _resp(message)
            if reply:
                reply = reply.strip()
                if not reply.endswith(('.', '!', '?')):
                    reply += '.'
                reply += ' Если захотите, подскажу свободные слоты и помогу записаться.'
        else:
            reply = ask(message, client_id=client_id, source="web", history=history)
        reply = _clean_assistant_text(reply)
        current_app.logger.info(f"Получен ответ от OpenAI: {reply}")

        # Сохраняем сообщение в базу данных
        try:
            chat_message = ChatMessage(
                user=client_id,  # используем client_id как user
                message=message
            )
            current_app.logger.info("Сохранение сообщения в базу данных")
            db.session.add(chat_message)
            db.session.commit()
            current_app.logger.info("Сообщение успешно сохранено")
        except Exception as db_error:
            current_app.logger.error(f"Ошибка при сохранении в БД: {str(db_error)}")
            # Продолжаем выполнение даже при ошибке БД

        # Логируем событие в аналитику (best-effort)
        try:
            analytics_payload = {
                "event": "chat_message",
                "context": "site_chat",
                "user_key": client_id or "",
                "type": "",
                "rule_id": "",
                "item_id": "",
                "meta": {
                    "message": message,
                    "response": reply,
                    "source": "site_web",
                },
                "ip": request.remote_addr or "",
                "user_agent": request.headers.get("User-Agent", "")
            }
            log_analytics_event(analytics_payload)
        except Exception as e:
            current_app.logger.warning(f"Не удалось записать событие аналитики chat_message: {e}")

        return jsonify({
            'response': reply,
            'status': 'success'
        })

    except OpenAIError as e:
        current_app.logger.error(f"OpenAI Error: {str(e)}")
        return jsonify({
            'error': 'Ошибка при обработке запроса к AI',
            'details': str(e)
        }), 502

    except Exception as e:
        current_app.logger.error(f"Unexpected error in chat handler: {str(e)}")
        return jsonify({
            'error': 'Внутренняя ошибка сервера',
            'details': str(e)
        }), 500
