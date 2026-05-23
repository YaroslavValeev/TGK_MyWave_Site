import os
import time
from datetime import datetime

from openai import OpenAI
from flask import current_app, session, has_app_context

from app.modules.logger import get_logger
from app.services.rules import ChatMode
from app.services.google_sheets_service import append_record
from app.services.openai_runtime_config import (
    log_openai_chat_config_first_request,
    resolve_chat_models_from_config,
)

logger = get_logger(__name__)

client = None  # OpenAI client будет инициализирован при первом вызове


def _openai_client_from_config(cfg: dict | None = None) -> OpenAI:
    """Создаёт OpenAI client; опционально через OPENAI_HTTP_PROXY / HTTPS_PROXY."""
    cfg = cfg or {}
    api_key = cfg.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in Flask config")
    proxy = (
        cfg.get("OPENAI_HTTP_PROXY")
        or os.getenv("OPENAI_HTTP_PROXY")
        or os.getenv("HTTPS_PROXY")
        or os.getenv("HTTP_PROXY")
    )
    if proxy:
        try:
            import httpx

            logger.info("[openai-client] using HTTP proxy for API requests")
            http_client = httpx.Client(proxy=proxy.strip(), timeout=60.0)
            return OpenAI(api_key=api_key, http_client=http_client)
        except Exception as exc:
            logger.warning("[openai-client] proxy init failed, direct connection: %s", exc)
    return OpenAI(api_key=api_key)


# Default model names used by the code and tests
DEFAULT_MODEL = "gpt-4.1-nano"
FALLBACK_MODEL = "gpt-4.1-nano"

# Внутренний маркер: ассистент не вернул текст (режим auto → fallback completions)
_ASSISTANT_EMPTY_REPLY = "Извините, ассистент не дал ответа."

# Сообщение пользователю при CHAT_BACKEND=assistant_only и пустом ответе (без fallback)
_USER_ASSISTANT_UNAVAILABLE = (
    "Сейчас не удалось получить ответ ассистента. Попробуйте ещё раз чуть позже."
)


def _chat_backend(cfg: dict) -> str:
    raw = (cfg.get("CHAT_BACKEND") or os.getenv("CHAT_BACKEND") or "completions").strip().lower()
    if raw not in ("auto", "completions", "assistant_only", "responses"):
        raw = "completions"
    if raw != "auto":
        return raw
    # auto: по умолчанию completions + assistant_prompt.md (стабильно для сайта).
    # Assistant API — только если явно CHAT_USE_ASSISTANT=1 и задан ASSISTANT_ID.
    use_assistant = str(
        cfg.get("CHAT_USE_ASSISTANT") or os.getenv("CHAT_USE_ASSISTANT") or ""
    ).strip().lower() in ("1", "true", "yes")
    assistant_id = cfg.get("ASSISTANT_ID") or os.getenv("ASSISTANT_ID")
    if use_assistant and assistant_id:
        return "auto"
    return "completions"

def _is_region_blocked_error(exc: Exception) -> bool:
    s = str(exc).lower()
    return "unsupported_country_region_territory" in s or (
        "country" in s and "region" in s and "not supported" in s
    )


def _is_model_not_found_error(exc: Exception) -> bool:
    s = str(exc).lower()
    return ("model_not_found" in s) or ("does not exist" in s) or ("do not have access" in s)


def _is_bad_request_error(exc: Exception) -> bool:
    """400 от API: часто несовместимые параметры Responses (temperature, формат input) или модель."""
    if type(exc).__name__ == "BadRequestError":
        return True
    return getattr(exc, "status_code", None) == 400


def _is_insufficient_quota_error(exc: Exception) -> bool:
    """429 / billing: повтор с другой моделью обычно бессмысленен (тот же ключ/проект)."""
    s = str(exc).lower()
    if "insufficient_quota" in s:
        return True
    if "429" in s and ("quota" in s or "billing" in s):
        return True
    name = type(exc).__name__
    if "RateLimit" in name and "quota" in s:
        return True
    return False


def _user_friendly_openai_error(exc: Exception, *, cfg: dict | None = None) -> str:
    """
    Превращает “сырой” текст ошибки OpenAI в релизно-понятное сообщение для UI.
    Не раскрывает внутренние детали/токены/большие payload.
    """
    ename = type(exc).__name__
    s_lower = str(exc).lower()
    status = getattr(exc, "status_code", None)

    # Конфиг / ключ (до запроса к API)
    if isinstance(exc, RuntimeError) and "OPENAI_API_KEY" in str(exc):
        return (
            "Чат не настроен: не задан OPENAI_API_KEY. "
            "Укажите ключ в .env (или переменных окружения) и перезапустите сервер."
        )

    # Типичные классы исключений SDK OpenAI (имена стабильны между версиями)
    if ename == "PermissionDeniedError" or status == 403:
        if _is_region_blocked_error(exc):
            return (
                "OpenAI недоступен с этого сервера (регион заблокирован). "
                "Для info-вопросов чат ответит из базы знаний; для полного AI "
                "настройте OPENAI_HTTP_PROXY в .env или CHAT_BACKEND=completions через прокси."
            )
        return (
            "Доступ к OpenAI запрещён (403). Проверьте ключ, права проекта и регион сервера."
        )
    if ename == "AuthenticationError" or (
        "invalid" in s_lower and "api" in s_lower and "key" in s_lower
    ):
        return (
            "Ошибка авторизации OpenAI: проверьте, что OPENAI_API_KEY указан верно и ключ не отозван."
        )
    if ename in ("APIConnectionError", "ConnectError", "ConnectionError"):
        return (
            "Не удалось подключиться к серверам OpenAI. Проверьте интернет, VPN и доступность api.openai.com."
        )
    if ename in ("APITimeoutError", "Timeout") or "timeout" in s_lower:
        return "Запрос к OpenAI занял слишком много времени. Попробуйте ещё раз через минуту."

    if ename == "BadRequestError" or status == 400:
        return (
            "Сейчас не удалось получить ответ: запрос отклонён API (параметры или модель). "
            "Проверьте GPTS_MODEL и CHAT_BACKEND; для проверки можно временно задать CHAT_BACKEND=completions. "
            "Подробности — в логах сервера (строка с BadRequest / 400)."
        )
    if _is_insufficient_quota_error(exc):
        return (
            "Сейчас не удалось получить ответ: исчерпана квота API OpenAI для этого ключа. "
            "Проверьте биллинг и пополнение баланса в кабинете OpenAI (тот же проект, что и API key)."
        )
    if ename == "RateLimitError" or (status == 429 and not _is_insufficient_quota_error(exc)):
        return (
            "Слишком много запросов к OpenAI (лимит скорости). Подождите около минуты и попробуйте снова."
        )
    if "empty response" in s_lower:
        return (
            "Сейчас не удалось получить ответ: модель вернула пустой текст. "
            "Попробуйте ещё раз или временно задайте CHAT_BACKEND=completions."
        )

    if _is_model_not_found_error(exc):
        gpts = (cfg or {}).get("GPTS_MODEL") if cfg else None
        fb = (cfg or {}).get("FALLBACK_MODEL") if cfg else None
        return (
            "Сейчас не удалось получить ответ: модель недоступна (нет доступа или неверное имя). "
            f"Проверьте переменные окружения GPTS_MODEL{f'={gpts}' if gpts else ''} "
            f"и FALLBACK_MODEL{f'={fb}' if fb else ''}."
        )
    return "Сейчас не удалось получить ответ. Попробуйте ещё раз чуть позже."


def _response_input_text(text: str) -> dict:
    return {"type": "input_text", "text": text}


def _history_to_responses_input(history: list | None, prompt: str) -> list[dict]:
    items: list[dict] = []
    if history:
        if not isinstance(history, list):
            raise ValueError("history must be a list of messages")
        for msg in history:
            if not isinstance(msg, dict):
                continue
            role = str(msg.get("role") or "user").strip().lower()
            if role not in ("user", "assistant", "system", "developer"):
                role = "user"
            content = msg.get("content")
            if content is None:
                continue
            items.append({"role": role, "content": [_response_input_text(str(content))]})
    items.append({"role": "user", "content": [_response_input_text(prompt)]})
    return items


def _extract_responses_text(resp) -> str | None:
    text = getattr(resp, "output_text", None)
    if text and str(text).strip():
        return str(text).strip()

    output = getattr(resp, "output", None) or []
    for item in output:
        if getattr(item, "type", None) != "message":
            continue
        content = getattr(item, "content", None) or []
        parts: list[str] = []
        for block in content:
            btype = getattr(block, "type", None)
            if btype in ("output_text", "text"):
                val = getattr(block, "text", None)
                if isinstance(val, str) and val.strip():
                    parts.append(val.strip())
                    continue
                text_obj = getattr(block, "text", None)
                val2 = getattr(text_obj, "value", None) if text_obj is not None else None
                if val2 and str(val2).strip():
                    parts.append(str(val2).strip())
        if parts:
            return "\n".join(parts).strip()
    return None


def _msg_created_at(msg) -> int:
    v = getattr(msg, "created_at", None)
    try:
        return int(v) if v is not None else 0
    except (TypeError, ValueError):
        return 0


def _extract_assistant_text(msg) -> str | None:
    """Достаёт текст из сообщения assistant (разные форматы content в Threads API)."""
    if not msg or getattr(msg, "role", None) != "assistant":
        return None
    parts = getattr(msg, "content", None) or []
    for block in parts:
        btype = getattr(block, "type", None)
        if btype == "text":
            t = getattr(block, "text", None)
            if t is not None:
                val = getattr(t, "value", None)
                if val and str(val).strip():
                    return str(val).strip()
    try:
        return msg.content[0].text.value.strip()
    except (IndexError, AttributeError):
        return None


def _extract_reply_for_current_run(
    client: OpenAI,
    thread_id: str,
    run_id: str,
    user_message_created_at: int,
    assistant_id: str,
) -> tuple[str | None, str]:
    """
    Текст ответа именно для данного run — не «последний assistant в thread».

    Порядок: list(run_id=…) → сообщения с msg.run_id == run_id → самый ранний assistant
    с created_at > user_message_created_at (ответ на этот ход диалога).
    """
    # 1) Фильтр API по run_id
    try:
        resp = client.beta.threads.messages.list(
            thread_id=thread_id,
            run_id=run_id,
            order="desc",
            limit=15,
        )
        for msg in resp.data:
            if msg.role == "assistant":
                text = _extract_assistant_text(msg)
                if text:
                    return text, "run_id_query"
    except TypeError:
        logger.debug("[chat-assistant] messages.list(run_id=) not supported by client")
    except Exception as e:
        logger.warning("[chat-assistant] messages.list(run_id=%s) failed: %s", run_id, e)

    # 2) Явное поле run_id на сообщении (надёжнее, чем «первый assistant сверху»)
    try:
        resp = client.beta.threads.messages.list(thread_id=thread_id, order="desc", limit=50)
        for msg in resp.data:
            if msg.role != "assistant":
                continue
            if getattr(msg, "run_id", None) != run_id:
                continue
            text = _extract_assistant_text(msg)
            if text:
                return text, "run_id_on_message"
    except Exception as e:
        logger.warning("[chat-assistant] run_id scan on thread failed: %s", e)

    # 3) Последний по времени assistant строго после user-сообщения (финальный ответ хода;
    #    при tool-цепочках может быть несколько assistant — берём самый новый).
    try:
        resp = client.beta.threads.messages.list(thread_id=thread_id, order="asc", limit=100)
        best_ts = -1
        best_text = None
        for msg in resp.data:
            if msg.role != "assistant":
                continue
            ts = _msg_created_at(msg)
            if ts <= user_message_created_at:
                continue
            text = _extract_assistant_text(msg)
            if text and ts > best_ts:
                best_ts = ts
                best_text = text
        if best_text:
            return best_text, "latest_assistant_after_user"
    except Exception as e:
        logger.warning("[chat-assistant] latest-assistant-after-user failed: %s", e)

    logger.warning(
        "[chat-assistant] extract_reply_for_run exhausted run_id=%s thread_id=%s assistant_id=%s",
        run_id,
        thread_id,
        assistant_id,
    )
    return None, "none"


def log_dialog(client_id, source, message, reply):
    """
    Логирует диалог в Google Sheets.
    """
    try:
        if not all([client_id, source, message, reply]):
            raise ValueError("Не все необходимые параметры предоставлены")
        values = [[client_id, source, message, reply, datetime.now().isoformat()]]
        append_record(
            current_app.config.get("SPREADSHEET_ID"),
            current_app.config.get("GOOGLE_SHEET_NAME"),
            values[0]
        )
        logger.info(f"Диалог успешно записан для клиента {client_id}")
    except Exception as e:
        logger.error(f"Ошибка записи диалога: {str(e)}")

def ask_with_assistant(prompt, client_id=None, source: str = "web"):
    """
    Общение с OpenAI Assistant API (база знаний).
    Хранит thread_id в flask session по client_id.
    """
    global client
    if client is None:
        client = _openai_client_from_config(current_app.config)

    assistant_id = current_app.config.get('ASSISTANT_ID')
    if not assistant_id:
        raise RuntimeError("ASSISTANT_ID is not set in Flask config")

    # Получаем или создаём thread_id для пользователя
    thread_key = f"thread_id_{client_id or 'anon'}"
    thread_id = session.get(thread_key)
    if not thread_id:
        thread = client.beta.threads.create()
        thread_id = thread.id
        session[thread_key] = thread_id

    # Отправляем сообщение пользователя (нужен created_at для fallback привязки к ходу)
    user_message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=prompt,
    )
    user_created_at = _msg_created_at(user_message)

    # Запускаем ассистента
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id
    )

    logger.info(
        "[chat-assistant] phase=start assistant_id=%s thread_id=%s run_id=%s",
        assistant_id,
        thread_id,
        run.id,
    )

    # Ожидаем завершения run
    run_status = None
    for _ in range(60):  # максимум 60 секунд ожидания
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run_status.status in ["completed", "failed", "cancelled", "expired"]:
            break
        time.sleep(1)

    last_err = None
    if run_status:
        err = getattr(run_status, "last_error", None)
        last_err = getattr(err, "message", None) if err else None
        logger.info(
            "[chat-assistant] phase=run_done assistant_id=%s thread_id=%s run_id=%s "
            "final_status=%s last_error=%s",
            assistant_id,
            thread_id,
            run.id,
            run_status.status,
            last_err,
        )

    if run_status and run_status.status != "completed":
        logger.warning(
            "[chat-assistant] phase=run_not_completed assistant_id=%s thread_id=%s run_id=%s "
            "status=%s last_error=%s",
            assistant_id,
            thread_id,
            run.id,
            run_status.status,
            last_err,
        )

    # Ответ появляется с задержкой — несколько попыток; извлечение привязано к run / ходу диалога
    for attempt in range(6):
        text, how = _extract_reply_for_current_run(
            client,
            thread_id,
            run.id,
            user_created_at,
            assistant_id,
        )
        if text:
            ln = len(text)
            logger.info(
                "[chat-assistant] phase=extract_ok assistant_id=%s thread_id=%s run_id=%s "
                "attempt=%s extract=%s text_len=%s",
                assistant_id,
                thread_id,
                run.id,
                attempt,
                how,
                ln,
            )
            if client_id and str(os.getenv("CHAT_SHEETS_LOG_ASSISTANT", "1")).lower() not in (
                "0",
                "false",
                "no",
            ):
                log_dialog(client_id, source, prompt, text)
            return text
        if attempt < 5:
            time.sleep(0.45)

    logger.warning(
        "[chat-assistant] phase=extract_fail assistant_id=%s thread_id=%s run_id=%s "
        "run_status=%s assistant_msg_found=0 text_len=0 reason=no_assistant_text",
        assistant_id,
        thread_id,
        run.id,
        getattr(run_status, "status", None) if run_status else None,
    )
    return _ASSISTANT_EMPTY_REPLY


def _chat_completions_reply(
    cfg: dict,
    prompt: str,
    mode: ChatMode,
    history: list | None,
    client_id: str | None,
    source: str,
    temperature: float | None,
    max_tokens: int | None,
    model: str | None,
    system_prompt_override: str | None = None,
) -> str:
    """Один запрос к Chat Completions с CHAT_SYSTEM_PROMPT и историей (ветка без Assistant API)."""
    global client
    if client is None:
        client = _openai_client_from_config(cfg or {})

    log_openai_chat_config_first_request(logger, cfg)

    g_norm, f_norm, _ = resolve_chat_models_from_config(cfg)
    if model is not None:
        chosen_model = model
    else:
        if mode == ChatMode.CHAT_API:
            chosen_model = g_norm or (cfg.get("GPTS_MODEL") if cfg else None)
        else:
            chosen_model = g_norm or DEFAULT_MODEL
    fallback_model = f_norm or FALLBACK_MODEL

    system_prompt = (
        system_prompt_override
        if system_prompt_override is not None
        else cfg.get("CHAT_SYSTEM_PROMPT", "You are a helpful assistant.")
    )
    messages = []
    if mode == ChatMode.CHAT_API:
        messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
    else:
        messages.append({"role": "system", "content": system_prompt})
        if history:
            if not isinstance(history, list):
                raise ValueError("history must be a list of messages")
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

    params = {
        "model": chosen_model,
        "messages": messages,
    }
    if temperature is not None:
        params["temperature"] = temperature
    if max_tokens is not None:
        params["max_tokens"] = max_tokens

    try:
        resp = client.chat.completions.create(**params)
    except Exception as e:
        # При исчерпании квоты повтор с другой моделью не помогает — не делаем лишний запрос.
        if _is_insufficient_quota_error(e):
            logger.warning(
                "[OpenAI] insufficient_quota model=%s — skip fallback retry (same key/project)",
                chosen_model,
            )
            raise
        # Если основной GPTS_MODEL не найден/недоступен — пробуем FALLBACK_MODEL (если отличается).
        if _is_model_not_found_error(e) and fallback_model and fallback_model != chosen_model:
            logger.warning(
                "[OpenAI] model_not_found for model=%s; retrying with fallback_model=%s",
                chosen_model,
                fallback_model,
            )
            params["model"] = fallback_model
            try:
                resp = client.chat.completions.create(**params)
            except Exception as e2:
                if _is_insufficient_quota_error(e2):
                    logger.warning(
                        "[OpenAI] fallback_model=%s also failed: insufficient_quota",
                        fallback_model,
                    )
                raise
        else:
            raise

    reply = resp.choices[0].message.content.strip() if resp.choices else None
    if not reply:
        raise RuntimeError("Empty response from OpenAI")
    if client_id:
        log_dialog(client_id, source, prompt, reply)
    logger.info(f"[OpenAI] mode={mode} client_id={client_id} success (chat completions)")
    return reply


def _responses_api_reply(
    cfg: dict,
    prompt: str,
    mode: ChatMode,
    history: list | None,
    client_id: str | None,
    source: str,
    temperature: float | None,
    max_tokens: int | None,
    model: str | None,
    instructions: str | None = None,
) -> str:
    """Один запрос к OpenAI Responses API с тем же внешним контрактом, что и completions."""
    global client
    if client is None:
        client = _openai_client_from_config(cfg or {})

    log_openai_chat_config_first_request(logger, cfg)

    if not hasattr(client, "responses"):
        raise RuntimeError(
            "Для Responses API нужен пакет openai>=1.70 с атрибутом client.responses. "
            "Обновите зависимости: pip install -r requirements.txt"
        )

    g_norm, f_norm, _ = resolve_chat_models_from_config(cfg)
    chosen_model = model or g_norm or DEFAULT_MODEL
    fallback_model = f_norm or FALLBACK_MODEL
    system_prompt = instructions or cfg.get("CHAT_SYSTEM_PROMPT", "You are a helpful assistant.")

    params = {
        "model": chosen_model,
        "instructions": system_prompt,
        "input": _history_to_responses_input(history, prompt),
    }
    if temperature is not None:
        params["temperature"] = temperature
    if max_tokens is not None:
        params["max_output_tokens"] = max_tokens

    try:
        resp = client.responses.create(**params)
    except Exception as e:
        if _is_insufficient_quota_error(e):
            logger.warning(
                "[OpenAI] insufficient_quota model=%s — skip fallback retry for responses (same key/project)",
                chosen_model,
            )
            raise
        if _is_model_not_found_error(e) and fallback_model and fallback_model != chosen_model:
            logger.warning(
                "[OpenAI] responses model_not_found for model=%s; retrying with fallback_model=%s",
                chosen_model,
                fallback_model,
            )
            params["model"] = fallback_model
            try:
                resp = client.responses.create(**params)
            except Exception as e2:
                if _is_insufficient_quota_error(e2):
                    raise
                if _is_bad_request_error(e2):
                    logger.warning(
                        "[OpenAI] responses.create BadRequest after model retry; "
                        "falling back to chat completions model=%s",
                        params.get("model"),
                        exc_info=True,
                    )
                    return _chat_completions_reply(
                        cfg,
                        prompt,
                        mode,
                        history,
                        client_id,
                        source,
                        temperature,
                        max_tokens,
                        model,
                        system_prompt_override=system_prompt,
                    )
                raise
        elif _is_bad_request_error(e):
            logger.warning(
                "[OpenAI] responses.create BadRequest; falling back to chat completions model=%s",
                chosen_model,
                exc_info=True,
            )
            return _chat_completions_reply(
                cfg,
                prompt,
                mode,
                history,
                client_id,
                source,
                temperature,
                max_tokens,
                model,
                system_prompt_override=system_prompt,
            )
        else:
            raise

    reply = _extract_responses_text(resp)
    if not reply:
        raise RuntimeError("Empty response from OpenAI Responses API")
    if client_id:
        log_dialog(client_id, source, prompt, reply)
    logger.info(f"[OpenAI] mode={mode} client_id={client_id} success (responses api)")
    return reply


def responses_text_reply(
    prompt: str,
    *,
    history: list | None = None,
    client_id: str | None = None,
    source: str = "web",
    temperature: float | None = None,
    max_tokens: int | None = None,
    model: str | None = None,
    instructions: str | None = None,
) -> str:
    """Публичная обёртка для Responses API без Assistant fallback."""
    cfg = current_app.config if has_app_context() else {}
    return _responses_api_reply(
        cfg,
        prompt,
        ChatMode.RESPONSES_API,
        history,
        client_id,
        source,
        temperature,
        max_tokens,
        model,
        instructions=instructions,
    )


def ask(
    prompt,
    mode: ChatMode = ChatMode.RESPONSES_API,
    history: list = None,
    client_id: str = None,
    source: str = "web",
    temperature: float = None,
    max_tokens: int = None,
    model: str | None = None,
    page_context: dict | None = None,
    knowledge_snippets: list | None = None,
) -> str:
    """
    Унифицированный интерфейс для обращения к OpenAI.
    page_context — контекст страницы/записи (mw_chat_context), см. chat_page_context.
    """
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt must be a non-empty string")
    try:
        cfg = current_app.config if has_app_context() else {}
        from app.services.chat_page_context import merge_chat_system_prompt

        sys_prompt = merge_chat_system_prompt(cfg, page_context)
        if knowledge_snippets:
            from app.services.responses_api import append_knowledge_to_system_prompt

            sys_prompt = append_knowledge_to_system_prompt(sys_prompt, knowledge_snippets)
        backend = _chat_backend(cfg)

        if backend == "completions":
            logger.info(
                "[chat-assistant] path=completions_only reason=CHAT_BACKEND=completions"
            )
            return _chat_completions_reply(
                cfg,
                prompt,
                mode,
                history,
                client_id,
                source,
                temperature,
                max_tokens,
                model,
                system_prompt_override=sys_prompt,
            )

        if backend == "responses":
            logger.info(
                "[chat-responses] path=responses_only reason=CHAT_BACKEND=responses"
            )
            return _responses_api_reply(
                cfg,
                prompt,
                mode,
                history,
                client_id,
                source,
                temperature,
                max_tokens,
                model,
                instructions=sys_prompt,
            )

        assistant_id = cfg.get("ASSISTANT_ID") if cfg else None
        if backend == "assistant_only" and not assistant_id:
            logger.warning(
                "[chat-assistant] CHAT_BACKEND=assistant_only but ASSISTANT_ID unset; "
                "using Chat Completions"
            )
            return _chat_completions_reply(
                cfg,
                prompt,
                mode,
                history,
                client_id,
                source,
                temperature,
                max_tokens,
                model,
                system_prompt_override=sys_prompt,
            )

        use_assistant = bool(assistant_id) and backend in ("auto", "assistant_only")

        if use_assistant:
            try:
                reply = ask_with_assistant(prompt, client_id=client_id, source=source)
            except Exception as exc:
                if backend == "assistant_only":
                    raise
                logger.warning(
                    "[chat-assistant] path=fallback_completions reason=assistant_exception err=%s",
                    exc,
                )
                return _chat_completions_reply(
                    cfg,
                    prompt,
                    mode,
                    history,
                    client_id,
                    source,
                    temperature,
                    max_tokens,
                    model,
                    system_prompt_override=sys_prompt,
                )
            empty = reply == _ASSISTANT_EMPTY_REPLY or not (reply or "").strip()

            if empty and backend == "assistant_only":
                logger.error(
                    "[chat-assistant] path=assistant_only_failed fallback=none "
                    "reason=empty_or_placeholder"
                )
                return _USER_ASSISTANT_UNAVAILABLE

            if empty:
                logger.warning(
                    "[chat-assistant] path=fallback_completions reason=assistant_empty_or_placeholder "
                    "detail=CHAT_BACKEND_auto"
                )
                return _chat_completions_reply(
                    cfg,
                    prompt,
                    mode,
                    history,
                    client_id,
                    source,
                    temperature,
                    max_tokens,
                    model,
                    system_prompt_override=sys_prompt,
                )
            logger.info(
                "[chat-assistant] path=assistant_ok backend=%s text_len=%s",
                backend,
                len(reply or ""),
            )
            return reply

        return _chat_completions_reply(
            cfg,
            prompt,
            mode,
            history,
            client_id,
            source,
            temperature,
            max_tokens,
            model,
            system_prompt_override=sys_prompt,
        )
    except Exception as e:
        cfg = current_app.config if has_app_context() else {}
        # В лог — полная причина; в UI — короткое сообщение.
        logger.error("[OpenAI] mode=%s client_id=%s error=%s", mode, client_id, e, exc_info=True)
        if has_app_context():
            try:
                current_app.logger.exception(
                    "[chat-openai] ask() failed; client_id=%s mode=%s",
                    client_id,
                    mode,
                )
            except Exception:
                pass
        return _user_friendly_openai_error(e, cfg=cfg)

def smart_gpt_response(message, context=None):
    try:
        return ask(message, history=context)
    except Exception as e:
        logger.error(f"smart_gpt_response error: {e}")
        return "Извините, произошла ошибка при обработке запроса."

def process_chat_message(message, context=None):
    try:
        return smart_gpt_response(message, context=context)
    except Exception as e:
        logger.error(f"chat processing error: {e}")
        return "Извините, ошибка при обработке запроса."

get_response = ask

def create_assistant(name, instructions, model="gpt-4.1-nano"):
    try:
        global client
        if client is None:
            client = _openai_client_from_config(current_app.config)
        assistant = client.beta.assistants.create(
            name=name,
            instructions=instructions,
            model=model
        )
        logger.info(f"[OpenAI] Assistant created: {assistant.id}")
        return assistant
    except Exception as e:
        logger.error(f"[OpenAI] Failed to create assistant: {e}")
        raise


# --- Structured JSON response helper for booking orchestrator ---
import json


def _ensure_client():
    global client
    if client is None:
        client = _openai_client_from_config(current_app.config)
    return client


def respond_structured(prompt: str, state: dict | None = None, tools: list | None = None) -> dict:
    """
    Ask the model to return a compact JSON describing intent/entities/next_step.

    - Uses Chat Completions function-calling when tools are provided (tool_choice="auto").
    - Falls back to parsing a JSON object from text content.
    """
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt must be a non-empty string")

    _ensure_client()

    model = current_app.config.get('GPTS_MODEL') or "gpt-4.1-nano"
    system_prompt = (
        "Ты оркестратор записи на тренировку. Определи intent пользователя "
        "('book','provide_date','provide_time','confirm','cancel','other'), выдели сущности "
        "(date, time, name, phone) и предложи next_step из: 'ask_date','ask_time','confirm','done','other'. "
        "Отвечай строго JSON без пояснений."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    params = {
        "model": model,
        "messages": messages,
        "temperature": 0,
    }

    # Request json_object format if supported by the model
    params["response_format"] = {"type": "json_object"}

    if tools:
        params["tools"] = tools
        params["tool_choice"] = "auto"

    try:
        resp = client.chat.completions.create(**params)
        choice = resp.choices[0].message
        # Tool calls path
        if getattr(choice, "tool_calls", None):
            calls = []
            for tc in choice.tool_calls:
                try:
                    calls.append({
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments or "{}"),
                    })
                except Exception:
                    calls.append({"name": tc.function.name, "arguments": {}})
            return {"tool_calls": calls}
        # Content JSON path
        content = choice.content or "{}"
        try:
            data = json.loads(content)
        except Exception:
            # Extract first JSON object as a fallback
            m = None
            depth = 0
            start = -1
            for i, ch in enumerate(content):
                if ch == '{':
                    if depth == 0:
                        start = i
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0 and start != -1:
                        m = content[start:i+1]
                        break
            data = json.loads(m) if m else {"raw": content}
        return data
    except Exception as e:
        logger.error(f"respond_structured error: {e}")
        return {"error": str(e)}
