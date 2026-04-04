from flask import Blueprint, request, jsonify, current_app
from app.services.openai_service import (
    get_response,
    ChatMode,
    DEFAULT_MODEL,
    responses_text_reply,
)
from app.services.openai_runtime_config import normalize_openai_model_id
from app.services.ai_router import get_user_chat_history, save_chat_message
from app.routes.api import get_knowledge

responses_bp = Blueprint('responses_api', __name__, url_prefix='/api/assistant')


def _knowledge_items_from_response(resp):
    """Извлекает список строк из ответа view get_knowledge (jsonify)."""
    if resp is None:
        return []
    data = resp.get_json(silent=True)
    if isinstance(data, list):
        return [str(x).strip() for x in data if str(x).strip()]
    return []


def _collect_knowledge_snippets(
    prompt_lower: str,
    max_per_type: int = 3,
    *,
    mw_chat_context: dict | None = None,
) -> list[str]:
    keywords = {
        'тренировк': 'training',
        'трюк': 'tricks',
        'польз': 'training',
        'зал': 'training',
        'техник': 'tricks',
    }
    relevant_types = set()
    for key, knowledge_type in keywords.items():
        if key in prompt_lower:
            relevant_types.add(knowledge_type)
    if mw_chat_context and isinstance(mw_chat_context, dict):
        sid = str(mw_chat_context.get("id") or "").lower().strip()
        title_lc = str(mw_chat_context.get("title") or "").lower()
        if sid == "gym" or "зал" in title_lc:
            relevant_types.add("training")
        if sid == "boat" or "катер" in title_lc:
            relevant_types.add("training")
    out: list[str] = []
    for knowledge_type in relevant_types:
        response = get_knowledge(knowledge_type)
        items = _knowledge_items_from_response(response)
        out.extend(items[:max_per_type])
    return out


@responses_bp.route('/', methods=['POST'])
def assistant():
    from app.services.ai_router import get_user_chat_history, save_chat_message
    data = request.get_json() or {}
    prompt       = data.get('prompt')
    client_id    = data.get('client_id', request.remote_addr)
    chat_history = data.get('history', get_user_chat_history(client_id))
    params       = data.get('params', {})

    # валидация
    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify(error="Поле 'prompt' должно быть непустым строковым"), 400

    temperature = params.get('temperature', None)
    max_tokens  = params.get('max_tokens', None)

    try:
        # получить ответ
        reply = get_response(
            prompt=prompt,
            mode=ChatMode.RESPONSES_API,
            history=chat_history,
            client_id=client_id,
            source="assistant_api",
            temperature=temperature,
            max_tokens=max_tokens
        )
        # сохранить историю
        save_chat_message(client_id, prompt, reply)

        return jsonify(response=reply), 200

    except ValueError as ve:
        # некорректные input-параметры
        return jsonify(error=str(ve)), 422
    except Exception:
        current_app.logger.exception("Ошибка в /api/assistant")
        return jsonify(error="Внутренняя ошибка сервера"), 500

def get_response_with_knowledge(prompt, context=None, *, mw_chat_context=None):
    """Ответ с подмешиванием выдержек из knowledge_base (info-intent в /chat/api)."""
    try:
        if not isinstance(prompt, str) or not prompt.strip():
            return None

        prompt_lower = prompt.lower()
        snippets = _collect_knowledge_snippets(prompt_lower, mw_chat_context=mw_chat_context)
        if not snippets:
            return None

        raw_m = current_app.config.get("GPTS_MODEL") or DEFAULT_MODEL
        model, mw = normalize_openai_model_id(str(raw_m), label="GPTS_MODEL")
        if not model:
            model = DEFAULT_MODEL
        if mw:
            current_app.logger.warning(mw)
        from app.services.chat_page_context import merge_chat_system_prompt

        base_prompt = merge_chat_system_prompt(current_app.config, mw_chat_context)
        kb_block = "\n".join(snippets[:15])
        system_content = (
            f"{base_prompt}\n\n"
            "Используй при ответе только релевантные факты из базы знаний ниже. "
            "Если фактов недостаточно, скажи об этом кратко.\n\n"
            f"{kb_block}"
        )

        messages = [{"role": "system", "content": system_content}]
        if context:
            if not isinstance(context, list):
                raise ValueError("context must be a list of messages")
            messages.extend(context)
        return responses_text_reply(
            prompt,
            history=messages[1:],
            source="knowledge",
            temperature=0.7,
            model=model,
            instructions=system_content,
        )

    except Exception as e:
        current_app.logger.error("Error generating knowledge response: %s", str(e))
        return "Извините, произошла ошибка. Попробуйте переформулировать вопрос."
