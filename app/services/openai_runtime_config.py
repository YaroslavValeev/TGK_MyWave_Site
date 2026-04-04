"""
Runtime-диагностика и нормализация конфигурации OpenAI для публичного чата.

Без логирования полного API key — только fingerprint и суффикс.
"""
from __future__ import annotations

import hashlib
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Частая опечатка: в .env пишут `gpt-4.1-min` вместо `gpt-4.1-mini` (без «i»).
# В логах OpenAI тогда фигурирует именно неверное имя — это не обрезка в коде.
KNOWN_MODEL_ALIASES: dict[str, str] = {
    "gpt-4.1-min": "gpt-4.1-mini",
}

_chat_config_logged_startup = False
_chat_config_logged_first_request = False


def fingerprint_openai_api_key(key: str | None) -> str:
    """Короткий отпечаток ключа: sha256 (12 hex) + последние 4 символа."""
    if not key or not str(key).strip():
        return "unset"
    s = str(key).strip()
    try:
        h = hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]
    except Exception:
        h = "?"
    tail = s[-4:] if len(s) >= 4 else "****"
    return f"sha256:{h}…tail:{tail}"


def normalize_openai_model_id(raw: str | None, *, label: str = "model") -> tuple[str, str | None]:
    """
    Возвращает (нормализованное_имя, предупреждение_или_None).
    """
    if raw is None:
        return "", None
    m = str(raw).strip()
    if not m:
        return "", None
    fixed = KNOWN_MODEL_ALIASES.get(m.lower())
    if fixed and fixed != m:
        warn = (
            f"[openai-config] {label}: исправлена известная опечатка в имени модели "
            f"'{m}' -> '{fixed}' (в коде нет обрезки 'mini'; проверьте .env)"
        )
        return fixed, warn
    return m, None


def resolve_chat_models_from_config(cfg: dict[str, Any]) -> tuple[str, str, list[str]]:
    """
    Эффективные GPTS_MODEL и FALLBACK_MODEL после нормализации + список предупреждений.
    """
    warnings: list[str] = []
    raw_g = (cfg.get("GPTS_MODEL") or "").strip() if cfg else ""
    raw_f = (cfg.get("FALLBACK_MODEL") or "").strip() if cfg else ""

    g, w1 = normalize_openai_model_id(raw_g or None, label="GPTS_MODEL")
    if w1:
        warnings.append(w1)
        logger.warning(w1)

    f, w2 = normalize_openai_model_id(raw_f or None, label="FALLBACK_MODEL")
    if w2:
        warnings.append(w2)
        logger.warning(w2)

    return g, f, warnings


def log_openai_chat_config_startup(app) -> None:
    """Один раз при старте приложения: backend, модели, fingerprint ключа, источник env."""
    global _chat_config_logged_startup
    if _chat_config_logged_startup:
        return
    _chat_config_logged_startup = True

    cfg = app.config
    g, f, warns = resolve_chat_models_from_config(cfg)
    key = cfg.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    fp = fingerprint_openai_api_key(key)

    raw_env_g = os.getenv("GPTS_MODEL")
    raw_env_f = os.getenv("FALLBACK_MODEL")
    raw_env_b = os.getenv("CHAT_BACKEND")

    backend = (cfg.get("CHAT_BACKEND") or raw_env_b or "auto").strip().lower()

    app.logger.info(
        "[openai-chat-config] startup CHAT_BACKEND=%s GPTS_MODEL=%s FALLBACK_MODEL=%s "
        "OPENAI_API_KEY_fp=%s dotenv_loaded=%s",
        backend,
        g or "(empty)",
        f or "(empty)",
        fp,
        bool(os.getenv("OPENAI_API_KEY") or cfg.get("OPENAI_API_KEY")),
    )
    if raw_env_g and g and raw_env_g.strip() != g:
        app.logger.info(
            "[openai-chat-config] GPTS_MODEL after normalization differs from raw env "
            "(raw len=%s, effective=%s)",
            len(raw_env_g.strip()),
            g,
        )
    for w in warns:
        app.logger.warning(w)


def log_openai_chat_config_first_request(logger_inst: logging.Logger, cfg: dict[str, Any]) -> None:
    """Один раз при первом вызове completions: подтверждение эффективных значений."""
    global _chat_config_logged_first_request
    if _chat_config_logged_first_request:
        return
    _chat_config_logged_first_request = True

    g, f, _ = resolve_chat_models_from_config(cfg)
    backend = (cfg.get("CHAT_BACKEND") or os.getenv("CHAT_BACKEND") or "auto").strip().lower()
    fp = fingerprint_openai_api_key(cfg.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"))

    logger_inst.info(
        "[openai-chat-config] first_completions_request CHAT_BACKEND=%s GPTS_MODEL=%s "
        "FALLBACK_MODEL=%s OPENAI_API_KEY_fp=%s",
        backend,
        g or "(empty)",
        f or "(empty)",
        fp,
    )
