import os

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

# Проекты: stem файла в knowledge_base/projects/*.txt
_PROJECT_KB_FILES: dict[str, str] = {
    "wakesurf_safari": "wakesurf_safari.txt",
    "wake_challenge": "wake_challenge.txt",
    "mywave_ruza_camp": "mywave_ruza_camp.txt",
}

# Длинные фразы раньше коротких (wakesurf safari > safari)
_PROJECT_SIGNALS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "wakesurf_safari",
        (
            "wakesurf safari",
            "wake surf safari",
            "вейк сафари",
            "вейксерф сафари",
            "сафари",
            "safari",
            "sufari",
        ),
    ),
    (
        "wake_challenge",
        (
            "wakesurf challenge",
            "wake surf challenge",
            "wake challenge",
            "вейк челлендж",
            "вейкчеллендж",
            "челлендж mywave",
            "challenge mywave",
            "wsc2025",
            "wsc 2025",
        ),
    ),
    (
        "mywave_ruza_camp",
        (
            "mywave ruza",
            "ruza camp",
            "руза кемп",
            "руза",
            "ruza",
            "лагер",
            "смена",
            "кемп",
            "camp",
        ),
    ),
)

_CTX_PROJECT_MAP: dict[str, str] = {
    "safari": "wakesurf_safari",
    "wakesurf_safari": "wakesurf_safari",
    "wakesurf-safari": "wakesurf_safari",
    "challenge": "wake_challenge",
    "wake_challenge": "wake_challenge",
    "wake-challenge": "wake_challenge",
    "wsc2025": "wake_challenge",
    "wakesurf-challenge": "wake_challenge",
    "wakesurf-challenge-2025": "wake_challenge",
    "ruza": "mywave_ruza_camp",
    "mywave_ruza_camp": "mywave_ruza_camp",
    "mywave-ruza-camp": "mywave_ruza_camp",
}


def _knowledge_items_from_response(resp):
    """Извлекает список строк из ответа view get_knowledge (jsonify)."""
    if resp is None:
        return []
    data = resp.get_json(silent=True)
    if isinstance(data, list):
        return [str(x).strip() for x in data if str(x).strip()]
    return []


def _knowledge_base_dir() -> str:
    return os.path.normpath(
        os.path.join(current_app.root_path, "..", "knowledge_base")
    )


def _read_project_paragraphs(project_key: str) -> list[str]:
    """Параграфы одного проекта из knowledge_base/projects/."""
    filename = _PROJECT_KB_FILES.get(project_key)
    if not filename:
        return []
    full_path = os.path.join(_knowledge_base_dir(), "projects", filename)
    if not os.path.isfile(full_path):
        return []
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        return [p.strip() for p in content.split("\n\n") if p.strip()]
    except OSError as exc:
        current_app.logger.error("kb_project_read_failed", extra={"file": filename, "err": str(exc)})
        return []


def _detect_project_keys(
    prompt_lower: str,
    mw_chat_context: dict | None = None,
) -> list[str]:
    """Какие проекты явно упомянуты в вопросе или контексте страницы."""
    found: list[str] = []
    seen: set[str] = set()

    def _add(key: str) -> None:
        if key in _PROJECT_KB_FILES and key not in seen:
            seen.add(key)
            found.append(key)

    if mw_chat_context and isinstance(mw_chat_context, dict):
        sid = str(mw_chat_context.get("id") or "").lower().strip()
        title_lc = str(mw_chat_context.get("title") or "").lower()
        if sid in _CTX_PROJECT_MAP:
            _add(_CTX_PROJECT_MAP[sid])
        for ctx_key, project_key in _CTX_PROJECT_MAP.items():
            if ctx_key in title_lc:
                _add(project_key)

    for project_key, aliases in _PROJECT_SIGNALS:
        for alias in aliases:
            if alias in prompt_lower:
                _add(project_key)
                break

    return found


def _score_project_paragraph(prompt_lower: str, project_key: str, paragraph: str) -> int:
    score = 0
    pl = paragraph.lower()
    for _pk, aliases in _PROJECT_SIGNALS:
        if _pk != project_key:
            continue
        for alias in aliases:
            if alias in prompt_lower and alias in pl:
                score += 12 + len(alias)
    if project_key.replace("_", " ") in pl:
        score += 5
    return score


def _collect_project_snippets(
    prompt_lower: str,
    *,
    mw_chat_context: dict | None = None,
    max_snippets: int = 4,
) -> list[str]:
    """Только релевантные проекты — без подмешивания Challenge при вопросе про Safari."""
    keys = _detect_project_keys(prompt_lower, mw_chat_context)
    if keys:
        out: list[str] = []
        for key in keys[:2]:
            out.extend(_read_project_paragraphs(key))
        return out[:max_snippets]

    # Общий вопрос про проекты — ранжируем только по реальному score сигналов.
    ranked: list[tuple[int, str]] = []
    for project_key in _PROJECT_KB_FILES:
        for para in _read_project_paragraphs(project_key):
            sc = _score_project_paragraph(prompt_lower, project_key, para)
            if sc > 0:
                ranked.append((sc, para))
    ranked.sort(key=lambda x: x[0], reverse=True)
    if ranked:
        return [p for _s, p in ranked[:max_snippets]]
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
        'катер': 'training',
        'катере': 'training',
        'техник': 'tricks',
        'проект': 'projects',
        'мероприят': 'projects',
        'соревнован': 'projects',
        'чемпионат': 'projects',
        'safari': 'projects',
        'сафари': 'projects',
        'sufari': 'projects',
        'challenge': 'projects',
        'wakesurf': 'projects',
        'вейк': 'projects',
        'попасть': 'projects',
        'участ': 'projects',
        'запис': 'training',
        'проходит': 'training',
        'проходят': 'training',
        'кемп': 'projects',
        'camp': 'projects',
        'лагер': 'projects',
        'ruza': 'projects',
        'руза': 'projects',
    }
    relevant_types = set()
    for key, knowledge_type in keywords.items():
        if key in prompt_lower:
            relevant_types.add(knowledge_type)
    if mw_chat_context and isinstance(mw_chat_context, dict):
        sid = str(mw_chat_context.get("id") or "").lower().strip()
        entry = str(mw_chat_context.get("entry") or "").lower().strip()
        title_lc = str(mw_chat_context.get("title") or "").lower()
        if sid == "gym" or "зал" in title_lc:
            relevant_types.add("training")
        if sid == "boat" or "катер" in title_lc:
            relevant_types.add("training")
        if entry == "projects" or sid in ("safari", "challenge", "wake_industry"):
            relevant_types.add("projects")
        if "safari" in title_lc or "соревн" in title_lc or "проект" in title_lc:
            relevant_types.add("projects")
    out: list[str] = []
    for knowledge_type in relevant_types:
        if knowledge_type == "projects":
            # Официальный чемпионат ≠ Wake Challenge: не подмешиваем все projects/*.txt
            if any(
                m in prompt_lower
                for m in (
                    "чемпионат россии",
                    "чемпионат рф",
                    "чемпионате россии",
                    "чемпионате рф",
                )
            ) and not any(
                m in prompt_lower
                for m in (
                    "wake challenge",
                    "вейк челлендж",
                    "wakesurf challenge",
                )
            ):
                continue
            project_bits = _collect_project_snippets(
                prompt_lower,
                mw_chat_context=mw_chat_context,
                max_snippets=max_per_type + 1,
            )
            if project_bits:
                out.extend(project_bits)
                continue
            # Не дампить весь каталог projects по слабому ключу «чемпионат/соревнован».
            if any(k in prompt_lower for k in ("чемпионат", "соревнован", "турнир")):
                continue
        response = get_knowledge(knowledge_type)
        items = _knowledge_items_from_response(response)
        out.extend(items[:max_per_type])
    try:
        from app.services.kb_chat.snippets import collect_chat_kb_snippets

        v2_snippets = collect_chat_kb_snippets(
            prompt_lower,
            mw_chat_context=mw_chat_context,
            max_snippets=max_per_type + 2,
        )
        if v2_snippets:
            out = v2_snippets + out
    except Exception as exc:
        current_app.logger.debug("kb_v2_snippets_failed", extra={"err": str(exc)})
    return out


_WHAT_TO_BRING_TRIGGERS = (
    "что взять",
    "что нужно с собой",
    "что брать с собой",
    "нужно брать",
)

_BOAT_BRING_MARKERS = ("катер", "катере", "на катере", "на воде", "boat")
_GYM_BRING_MARKERS = ("зал", "зале", "в зал", "помещен", "gym")


def what_to_bring_location(text_lc: str, mw_chat_context: dict | None = None) -> str | None:
    """'boat' | 'gym' | None — явная локация в вопросе или контексте страницы."""
    if mw_chat_context and isinstance(mw_chat_context, dict):
        sid = str(mw_chat_context.get("id") or "").lower().strip()
        if sid == "boat":
            return "boat"
        if sid == "gym":
            return "gym"
        title_lc = str(mw_chat_context.get("title") or "").lower()
        if "катер" in title_lc:
            return "boat"
        if "зал" in title_lc:
            return "gym"
    if any(m in text_lc for m in _BOAT_BRING_MARKERS):
        return "boat"
    if any(m in text_lc for m in _GYM_BRING_MARKERS):
        return "gym"
    return None


def try_direct_what_to_bring_reply(
    text_lc: str,
    mw_chat_context: dict | None = None,
) -> str | None:
    """Прямой чек-лист «что взять», если локация уже ясна (катер или зал)."""
    from app.services.kb_chat.direct_replies import try_direct_what_to_bring_reply as _kb_what_to_bring

    result = _kb_what_to_bring(text_lc, mw_chat_context)
    return result.text if result else None


def append_knowledge_to_system_prompt(base_prompt: str, snippets: list[str]) -> str:
    """Добавляет выдержки KB в system prompt для fallback ask()."""
    if not snippets:
        return base_prompt
    kb_block = "\n".join(snippets[:15])
    return (
        f"{base_prompt}\n\n"
        "Используй при ответе только факты из базы знаний ниже. "
        "Отвечай строго по проекту/теме вопроса пользователя — не подменяй Safari на Challenge, "
        "кемп на сафари и т.п. Если фактов недостаточно, честно скажи об этом кратко.\n\n"
        f"{kb_block}"
    )


def format_offline_kb_reply(snippets: list[str], *, max_chars: int = 900) -> str:
    """Собирает читаемый ответ из KB без вызова OpenAI (для RU-серверов / geo-block)."""
    if not snippets:
        return ""
    parts: list[str] = []
    total = 0
    for raw in snippets[:5]:
        chunk = str(raw).strip()
        if not chunk:
            continue
        if total + len(chunk) > max_chars:
            room = max_chars - total - 3
            if room <= 40:
                break
            chunk = chunk[:room].rstrip() + "..."
        parts.append(chunk)
        total += len(chunk)
        if total >= max_chars:
            break
    return "\n\n".join(parts).strip()


def try_offline_kb_reply(
    snippets: list[str],
    *,
    add_cta: bool = True,
) -> str | None:
    """Готовый ответ для чата только из базы знаний."""
    body = format_offline_kb_reply(snippets)
    if not body:
        return None
    if add_cta and not body.endswith((".", "!", "?")):
        body += "."
    if add_cta:
        body += " Если захотите, подскажу свободные слоты и помогу записаться."
    return body


def is_openai_failure_reply(text: str | None) -> bool:
    if not text:
        return True
    t = str(text).strip().lower()
    markers = (
        "не удалось получить ответ",
        "ai временно недоступен",
        "умный ассистент временно недоступен",
        "сервис временно недоступен",
        "не удалось подключиться",
        "openai недоступен",
        "регион заблокирован",
        "unsupported_country",
    )
    return any(m in t for m in markers)


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
            "Отвечай строго по проекту из вопроса (Safari / Challenge / Ruza Camp) — "
            "не подменяй один проект другим. "
            "Если фактов недостаточно, скажи об этом кратко. "
            "Пиши простым человеческим языком, без markdown-разметки, без символов ** и #, "
            "без заголовков и служебных меток.\n\n"
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
        return None
