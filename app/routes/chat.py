from flask import Blueprint, jsonify, request, current_app, render_template, session
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

# Отдельная страница чата удалена - используется только плавающий чат на главной странице
# @chat_bp.route("/")
# def chat_page():
#     messages = ChatMessage.query.order_by(ChatMessage.created_at.asc()).all()
#     return render_template("chat.html", messages=messages)

@chat_bp.route("/api", methods=["POST"])
def chat_handler():
    try:
        current_app.logger.info("Получен новый запрос к чату")
        # Be tolerant to client-side variations: if body isn't valid JSON, do not crash with BadRequest.
        data = request.get_json(silent=True)
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
        
        # Fallback: если сообщение похоже на запрос на бронирование, перенаправляем в booking API
        import re
        text_lc = message.lower().strip()
        
        # СНАЧАЛА проверяем информационный intent (вопросы, объяснения)
        # Эти запросы НЕ должны уходить в booking flow
        info_keywords = (
            'как ', 'что такое', 'объясни', 'поясни', 'расскажи', 'подскажи',
            'трик', 'трюк', 'олли', '360', 'разворот', 'поворот',
            'соревнован', 'подготов', 'готовить', 'научить', 'обуч',
            'что нужно', 'какие', 'какой', 'когда будут', 'где пройд'
        )
        info_intent = any(kw in text_lc for kw in info_keywords)
        
        # Проверяем booking intent ТОЛЬКО если это не информационный запрос
        # Исключаем "ближайш" для вопросов о соревнованиях/событиях
        booking_keywords = r'(?:хочу\s*)?(?:запис|бронь|заняти|слот|свободн\w*\s*врем)|сегодня|завтра|послезавтра|после\s*завтра'
        is_booking_request = re.search(booking_keywords, text_lc, re.IGNORECASE) and not info_intent
        
        # Также не уходим в booking если уже спрашивают про "ближайш" + "соревнован/событ/турнир"
        if 'ближайш' in text_lc and any(w in text_lc for w in ('соревнован', 'событи', 'турнир', 'чемпионат')):
            is_booking_request = False
            info_intent = True
        
        if is_booking_request:
            current_app.logger.info(f"Обнаружен запрос на бронирование, перенаправление в /api/booking")
            # Перенаправляем в booking API
            from flask import redirect, url_for
            from app.services.booking_orchestrator import orchestrate
            try:
                state = session.get('booking_state', {})
                reply_text, updated_state = orchestrate(message, state)
                session['booking_state'] = updated_state
                # Формируем suggestions
                suggestions = []
                step = updated_state.get('step')
                if step == 'ask_date':
                    suggestions = ['сегодня', 'завтра', 'послезавтра']
                elif step == 'ask_time' and updated_state.get('date'):
                    from app.services.tools import get_available_slots
                    try:
                        slots = get_available_slots(updated_state['date'])
                        suggestions = [s.get('time') for s in (slots or [])][:6]
                    except Exception:
                        suggestions = []
                elif step == 'confirm':
                    suggestions = ['Да', 'Нет']
                return jsonify(response=reply_text, state=updated_state, suggestions=suggestions)
            except Exception as exc:
                current_app.logger.error(f"Ошибка при обработке бронирования: {exc}", exc_info=True)
                return jsonify(
                    response="Сервис записи временно недоступен. Попробуйте чуть позже.",
                    state=session.get('booking_state', {}),
                    suggestions=[],
                ), 200

        # Получаем ответ от OpenAI
        current_app.logger.info("Отправка запроса к OpenAI")
        
        # Сбрасываем booking state если это информационный запрос
        if info_intent and session.get('booking_state'):
            current_app.logger.info("Сброс booking_state для информационного запроса")
            session.pop('booking_state', None)
        
        if info_intent:
            from app.services.responses_api import get_response_with_knowledge as _resp
            try:
                reply = _resp(message)
            except Exception as exc:
                current_app.logger.warning("Knowledge-base response failed, falling back to chat: %s", exc, exc_info=True)
                reply = None
            if reply:
                reply = reply.strip()
                if not reply.endswith(('.', '!', '?')):
                    reply += '.'
                reply += ' Если захотите, подскажу свободные слоты и помогу записаться.'
            else:
                # Fallback to regular chat if knowledge base did not return an answer
                reply = ask(message, client_id=client_id, source="web", history=history)
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
        current_app.logger.error("OpenAI Error: %s", str(e), exc_info=True)
        # Keep UX stable for the chat widget: respond with 200 and a user-friendly message.
        return jsonify({
            'response': 'Извините, AI временно недоступен. Попробуйте позже.',
            'status': 'error'
        }), 200

    except Exception as e:
        current_app.logger.error("Unexpected error in chat handler: %s", str(e), exc_info=True)
        return jsonify({
            'response': 'Извините, сервис временно недоступен. Попробуйте позже.',
            'status': 'error'
        }), 200
