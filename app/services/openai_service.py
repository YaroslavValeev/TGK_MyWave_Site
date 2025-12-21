import logging
import os
from openai import OpenAI
from flask import current_app, session
from app.services.rules import ChatMode
from app.services.google_sheets_service import append_record
from datetime import datetime
import time
import io
from typing import List

logger = logging.getLogger(__name__)

client = None  # OpenAI client будет инициализирован при первом вызове

# Compatibility constants expected by tests
DEFAULT_MODEL = "gpt-4"
FALLBACK_MODEL = "gpt-3.5-turbo"


def _get_openai_timeout_seconds() -> float:
    """
    Timeout for OpenAI requests.

    NOTE: keep it configurable without logging secrets.
    """
    try:
        value = current_app.config.get("OPENAI_TIMEOUT_SECONDS")
        if value is None:
            value = os.getenv("OPENAI_TIMEOUT_SECONDS", "30")
        return float(value)
    except Exception:
        return 30.0


def _init_client() -> OpenAI:
    global client
    if client is not None:
        return client

    api_key = current_app.config.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in Flask config")

    timeout_seconds = _get_openai_timeout_seconds()

    # OpenAI SDK supports `timeout` and `max_retries` in recent versions.
    # Keep compatibility by falling back to the minimal constructor if needed.
    try:
        client = OpenAI(api_key=api_key, timeout=timeout_seconds, max_retries=2)
    except TypeError:
        client = OpenAI(api_key=api_key)

    return client


def _select_chat_model(mode: ChatMode) -> str:
    """
    Pick a model for the chat widget.
    
    Priority:
    1. FINE_TUNED_MODEL — дообученная модель (приоритет для чата)
    2. GPTS_MODEL — основная модель
    3. FALLBACK_MODEL — запасная модель
    4. gpt-4o-mini — дефолт
    """
    DEFAULT_MODEL = "gpt-4o-mini"
    
    # Получаем модели из конфига/окружения
    fine_tuned = current_app.config.get("FINE_TUNED_MODEL") or os.getenv("FINE_TUNED_MODEL")
    preferred = current_app.config.get("GPTS_MODEL") or os.getenv("GPTS_MODEL")
    fallback = current_app.config.get("FALLBACK_MODEL") or os.getenv("FALLBACK_MODEL")

    # Защита: если значение похоже на API ключ (sk-...), игнорируем его
    def is_valid_model(m):
        if not m:
            return False
        if m.startswith("sk-"):
            logger.warning(f"[OpenAI] Модель '{m[:20]}...' похожа на API ключ! Игнорируем.")
            return False
        return True
    
    # Приоритет: fine-tuned → preferred → fallback → default
    if is_valid_model(fine_tuned):
        logger.info(f"[OpenAI] Используем FINE_TUNED_MODEL: {fine_tuned[:30]}...")
        return fine_tuned
    if is_valid_model(preferred):
        return preferred
    if is_valid_model(fallback):
        return fallback
    
    return DEFAULT_MODEL


def get_response(prompt: str, model: str | None = None, temperature: float = 0.7, max_tokens: int = 1000):
    """
    Compatibility wrapper expected by unit tests. Tries to call the chat
    completion and returns raw text. On first failure tries a fallback model.
    """
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt must be a non-empty string")

    _init_client()
    chosen_model = model or DEFAULT_MODEL
    # If client is a MagicMock in tests it will have the necessary attributes.
    try:
        resp = client.chat.completions.create(
            model=chosen_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        # handle mocked structure used in tests
        choice = getattr(resp, 'choices', None) or []
        if choice:
            # tests sometimes place content on .message.content
            first = choice[0]
            # try common locations
            if hasattr(first, 'message') and hasattr(first.message, 'content'):
                return first.message.content
            if hasattr(first, 'content'):
                return first.content
            return str(first)
        return str(resp)
    except Exception as e:
        # Try fallback model once
        if chosen_model != FALLBACK_MODEL:
            try:
                resp = client.chat.completions.create(
                    model=FALLBACK_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                choice = getattr(resp, 'choices', None) or []
                if choice:
                    first = choice[0]
                    if hasattr(first, 'message') and hasattr(first.message, 'content'):
                        return first.message.content
                    if hasattr(first, 'content'):
                        return first.content
                    return str(first)
                return str(resp)
            except Exception as inner_e:
                logger.exception("OpenAI fallback model request failed")
                return "Извините, не удалось получить ответ от AI. Попробуйте позже."
        logger.exception("OpenAI request failed")
        return "Извините, не удалось получить ответ от AI. Попробуйте позже."

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

def ask_with_assistant(prompt, client_id=None):
    """
    Общение с OpenAI Assistant API (база знаний).
    Хранит thread_id в flask session по client_id.
    """
    _init_client()

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

    # Отправляем сообщение пользователя
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=prompt
    )

    # Запускаем ассистента
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id
    )

    # Ожидаем завершения run
    for _ in range(60):  # максимум 60 секунд ожидания
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run_status.status in ["completed", "failed", "cancelled"]:
            break
        time.sleep(1)

    # Получаем последнее сообщение ассистента
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    for msg in reversed(messages.data):
        if msg.role == "assistant":
            return msg.content[0].text.value
    return "Извините, ассистент не дал ответа."

def ask(
    prompt,
    mode: ChatMode = ChatMode.RESPONSES_API,
    history: list = None,
    client_id: str = None,
    source: str = "web",
    temperature: float = None,
    max_tokens: int = None
) -> str:
    """
    Унифицированный интерфейс для обращения к OpenAI.
    """
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt must be a non-empty string")
    try:
        # Если передан history с контекстом — используем chat completions напрямую
        # (Assistant API не поддерживает кастомный системный промпт на лету)
        use_assistant = False
        assistant_id = current_app.config.get('ASSISTANT_ID')
        if assistant_id and not history:
            # Используем ассистента только если нет кастомного history
            use_assistant = True
        
        if use_assistant:
            logger.info(f"[OpenAI] Используем Assistant API (ASSISTANT_ID={assistant_id[:8]}...)")
            return ask_with_assistant(prompt, client_id=client_id)
        
        # Chat completions с поддержкой history
        _init_client()
        model = _select_chat_model(mode)
        logger.info(f"[OpenAI] Используем Chat Completions (model={model}, history_len={len(history) if history else 0})")

        system_prompt = current_app.config.get('CHAT_SYSTEM_PROMPT', "You are a helpful assistant.")
        messages = []
        if mode == ChatMode.CHAT_API:
            messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
        else:
            if history:
                if not isinstance(history, list):
                    raise ValueError("history must be a list of messages")
                messages.extend(history)
            messages.append({"role": "user", "content": prompt})

        params = {
            "model": model,
            "messages": messages
        }
        if temperature is not None:
            params["temperature"] = temperature
        if max_tokens is not None:
            params["max_tokens"] = max_tokens

        resp = client.chat.completions.create(**params)
        reply = resp.choices[0].message.content.strip() if resp.choices else None
        if not reply:
            raise RuntimeError("Empty response from OpenAI")
        if client_id:
            log_dialog(client_id, source, prompt, reply)
        logger.info(f"[OpenAI] mode={mode} client_id={client_id} success")
        return reply
    except Exception as e:
        logger.error(f"[OpenAI] mode={mode} client_id={client_id} error: {e}")
        # Do not leak internal exception details (which may include API keys)
        return "Извините, не удалось получить ответ от AI. Попробуйте позже."

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

def create_assistant(name, instructions, model="gpt-4-turbo"):
    try:
        _init_client()
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
    return _init_client()


def respond_structured(prompt: str, state: dict | None = None, tools: list | None = None) -> dict:
    """
    Ask the model to return a compact JSON describing intent/entities/next_step.

    - Uses Chat Completions function-calling when tools are provided (tool_choice="auto").
    - Falls back to parsing a JSON object from text content.
    """
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt must be a non-empty string")

    _ensure_client()

    model = current_app.config.get('GPTS_MODEL') or "gpt-4o-mini"
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


def get_embedding_vector(text: str) -> List[float]:
    """
    Получает embedding-вектор для текста через OpenAI.
    Использует существующий OpenAI client (см. _init_client).
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text must be a non-empty string")

    _init_client()
    model = current_app.config.get("RAG_EMBEDDING_MODEL", "text-embedding-3-small")
    resp = client.embeddings.create(model=model, input=text)
    return list(resp.data[0].embedding)


def transcribe_audio(file_storage) -> str:
    """
    Принимает werkzeug FileStorage с аудио и возвращает текст.
    Включается через ENABLE_VOICE.
    """
    _init_client()

    audio_bytes = file_storage.read()
    try:
        file_storage.seek(0)
    except Exception:
        pass

    bio = io.BytesIO(audio_bytes)
    # openai python expects a file-like object with a name
    bio.name = getattr(file_storage, "filename", None) or "audio.wav"

    resp = client.audio.transcriptions.create(
        model="gpt-4o-transcribe",
        file=bio,
    )
    return (getattr(resp, "text", None) or "").strip()
