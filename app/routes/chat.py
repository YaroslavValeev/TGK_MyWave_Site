import re
from flask import Blueprint, jsonify, request, current_app, render_template, session
from app.database.models import ChatMessage, db  # ChatMessage должен быть связан с db из app.database
from app.services.openai_service import ask
from app.services.google_sheets_analytics import log_analytics_event
from app.extensions import limiter
from flask_limiter.util import get_remote_address
from flask_limiter.errors import RateLimitExceeded
from openai import OpenAIError

chat_bp = Blueprint('chat', __name__, template_folder='../templates', url_prefix='/chat')


@chat_bp.errorhandler(RateLimitExceeded)
def _chat_rate_limit_exceeded(_e):
    return jsonify(
        response='Слишком много сообщений. Подождите около минуты и попробуйте снова.',
        status='rate_limited',
    ), 429

# Роль «assistant» в поле user для пар к user-сообщениям (схема без отдельной колонки role)
_ASSISTANT_USER = "assistant"


_ALLOWED_CONTEXT_ENTRIES = frozenset({"general", "services", "shop", "projects", "home"})
_ALLOWED_CONTEXT_KINDS = frozenset({"section", "service", "product", "project", ""})


def _sanitize_chat_context(raw) -> dict | None:
    """Допустимые поля контекста с страницы (услуги / магазин / проекты)."""
    if not isinstance(raw, dict):
        return None
    entry = str(raw.get("entry") or "general").lower().strip()
    if entry not in _ALLOWED_CONTEXT_ENTRIES:
        entry = "general"
    kind = str(raw.get("kind") or "").lower().strip()
    if kind not in _ALLOWED_CONTEXT_KINDS:
        kind = ""
    cid = str(raw.get("id") or "").strip()[:64]
    if cid and not re.match(r"^[\w\-.]+$", cid):
        cid = ""
    title = str(raw.get("title") or "").strip()[:120]
    out = {"entry": entry, "kind": kind, "id": cid, "title": title}
    if entry == "general" and not kind and not cid and not title:
        return None
    return out


def _truncate_log_field(text, max_len: int = 400):
    if text is None:
        return ""
    s = str(text)
    return s if len(s) <= max_len else s[:max_len] + "…"


def _needs_location_disambiguation(text_lc: str, mw_ctx: dict | None) -> bool:
    """
    Для вопроса «что взять/что нужно с собой» при общем контексте
    задаём короткое уточнение «зал или катер», чтобы не давать нерелевантный чек-лист.
    """
    if mw_ctx and isinstance(mw_ctx, dict):
        sid = str(mw_ctx.get("id") or "").lower().strip()
        entry = str(mw_ctx.get("entry") or "").lower().strip()
        title_lc = str(mw_ctx.get("title") or "").lower()
        if sid in ("gym", "boat"):
            return False
        if entry in ("services", "shop", "projects"):
            return False
        if "зал" in title_lc or "катер" in title_lc:
            return False
    ask_what_to_bring = (
        "что взять" in text_lc
        or "что нужно с собой" in text_lc
        or "что брать с собой" in text_lc
        or "нужно брать" in text_lc
    )
    return ask_what_to_bring


def _save_chat_turn(client_id: str, user_text: str, assistant_text: str | None) -> None:
    """Политика persistence: в chat_message пишутся и user, и assistant (роль assistant — поле user='assistant')."""
    try:
        db.session.add(ChatMessage(user=client_id or "anon", message=user_text))
        if assistant_text:
            db.session.add(ChatMessage(user=_ASSISTANT_USER, message=assistant_text))
        db.session.commit()
    except Exception as db_error:
        db.session.rollback()
        current_app.logger.error("Ошибка при сохранении чата в БД: %s", db_error)


def _chat_rate_limit_decorator(f):
    if limiter is None:
        return f
    return limiter.limit("40 per minute", key_func=get_remote_address)(f)

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

@chat_bp.route("", methods=["GET"])
@chat_bp.route("/", methods=["GET"])
def chat_page():
    """Страница «Чат»: тот же плавающий виджет из base.html, виджет открывается скриптом. Два маршрута — /chat и /chat/."""
    return render_template(
        "chat_page.html",
        title="Чат с экспертом",
        meta_description="Чат с AI-экспертом MyWave: вейксерф, тренировки, запись на занятие.",
    )


@chat_bp.route("/api", methods=["POST"])
@_chat_rate_limit_decorator
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
        ctx_in = _sanitize_chat_context(data.get("context"))
        if ctx_in is not None:
            session["mw_chat_context"] = ctx_in
        elif "context" in data and data.get("context") in (None, {}, ""):
            session.pop("mw_chat_context", None)

        if not message or not isinstance(message, str):
            current_app.logger.error(f"Некорректное сообщение: {message}")
            return jsonify({'error': 'Некорректное сообщение'}), 400

        # Идентификатор пользователя для контекста чата
        client_id = request.headers.get("X-User-Id") or request.remote_addr
        current_app.logger.info(f"Обработка сообщения от пользователя {client_id}: {message}")
        
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
            current_app.logger.info("Запрос на бронирование: сценарий booking_orchestrator через /chat/api")
            from app.services.booking_orchestrator import orchestrate
            try:
                state = dict(session.get("booking_state") or {})
                mw_ctx = session.get("mw_chat_context")
                if mw_ctx:
                    state["mw_context"] = mw_ctx
                reply_text, updated_state = orchestrate(message, state)
                if mw_ctx:
                    updated_state["mw_context"] = mw_ctx
                session["booking_state"] = {
                    k: v for k, v in updated_state.items() if k != "mw_context"
                }
                suggestions = []
                step = updated_state.get("step")
                if step == "ask_date":
                    suggestions = ["сегодня", "завтра", "послезавтра"]
                elif step == "ask_time" and updated_state.get("date"):
                    from app.services.tools import get_available_slots
                    try:
                        slots = get_available_slots(updated_state["date"])
                        suggestions = [s.get("time") for s in (slots or [])][:6]
                    except Exception:
                        suggestions = []
                elif step == "confirm":
                    suggestions = ["Да", "Нет"]
                _save_chat_turn(client_id, message, reply_text)
                return jsonify(response=reply_text, state=updated_state, suggestions=suggestions)
            except Exception as exc:
                current_app.logger.error(f"Ошибка при обработке бронирования: {exc}", exc_info=True)
                err_reply = "Сервис записи временно недоступен. Попробуйте чуть позже."
                _save_chat_turn(client_id, message, err_reply)
                return jsonify(
                    response=err_reply,
                    state=session.get("booking_state", {}),
                    suggestions=[],
                ), 200

        # Получаем ответ от OpenAI
        current_app.logger.info("Отправка запроса к OpenAI")
        
        # Сбрасываем booking state если это информационный запрос
        if info_intent and session.get('booking_state'):
            current_app.logger.info("Сброс booking_state для информационного запроса")
            session.pop('booking_state', None)
        
        mw_ctx = session.get("mw_chat_context")

        if info_intent:
            if _needs_location_disambiguation(text_lc, mw_ctx):
                reply = "Уточните, пожалуйста: вам нужна запись в зал или на катер? Тогда дам точный список, что взять с собой."
                _save_chat_turn(client_id, message, reply)
                return jsonify({'response': reply, 'status': 'success'})
            from app.services.responses_api import get_response_with_knowledge as _resp
            try:
                reply = _resp(message, mw_chat_context=mw_ctx)
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
                reply = ask(
                    message,
                    client_id=client_id,
                    source="web",
                    history=history,
                    page_context=mw_ctx,
                )
        else:
            reply = ask(
                message,
                client_id=client_id,
                source="web",
                history=history,
                page_context=mw_ctx,
            )
        reply = _clean_assistant_text(reply)
        current_app.logger.info(f"Получен ответ от OpenAI: {reply}")

        _save_chat_turn(client_id, message, reply)

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
                    "message": _truncate_log_field(message),
                    "response": _truncate_log_field(reply),
                    "source": "site_web",
                    "chat_context": session.get("mw_chat_context") or {},
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
