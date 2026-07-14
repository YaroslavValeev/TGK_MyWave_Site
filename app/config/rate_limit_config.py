"""Flask-Limiter configuration (env-driven, no hardcoded global caps)."""

from __future__ import annotations

import os
from typing import List, Tuple


def _env_bool(key: str, default: str = "0") -> bool:
    return os.getenv(key, default).strip().lower() in ("1", "true", "yes", "on")


def _parse_limit_list(raw: str) -> Tuple[str, ...]:
    value = (raw or "").strip()
    if not value or value.lower() in ("none", "off", "false", "0", ""):
        return tuple()
    parts = [part.strip() for part in value.split(",") if part.strip()]
    return tuple(parts)


class RateLimitConfig:
    """Central rate-limit contract for Site (P0: no global 200/day cap)."""

    ENABLED = not _env_bool("RATELIMIT_DISABLED", "0")
    STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")

    # Empty by default — public HTML/static must not share a small global bucket.
    DEFAULT_LIMITS: Tuple[str, ...] = _parse_limit_list(os.getenv("RATELIMIT_DEFAULT_LIMITS", ""))

    TRUST_PROXY = _env_bool("TRUST_PROXY", "1")
    PROXY_X_FOR = int(os.getenv("PROXY_X_FOR", "1") or "1")
    PROXY_X_PROTO = int(os.getenv("PROXY_X_PROTO", "1") or "1")
    PROXY_X_HOST = int(os.getenv("PROXY_X_HOST", "1") or "1")

    AUTH_LOGIN = os.getenv("RATELIMIT_AUTH_LOGIN", "5 per minute")
    ADMIN_LOGIN = os.getenv("RATELIMIT_ADMIN_LOGIN", "5 per minute")
    BOOKING_CREATE = os.getenv("RATELIMIT_BOOKING_CREATE", "10 per minute")
    BOOKING_API = os.getenv("RATELIMIT_BOOKING_API", "60 per minute")
    FORM_SUBMIT = os.getenv("RATELIMIT_FORM_SUBMIT", "5 per minute")
    CHAT_API = os.getenv("RATELIMIT_CHAT_API", "40 per minute")
    PAYMENT = os.getenv("RATELIMIT_PAYMENT", "5 per minute")
    ONLINE_COACHING = os.getenv("RATELIMIT_ONLINE_COACHING", "5 per minute")
    SHOP_FORM = os.getenv("RATELIMIT_SHOP_FORM", "10 per minute")
    SOCIAL_FORM = os.getenv("RATELIMIT_SOCIAL_FORM", "5 per minute")
    PROJECT_FORM = os.getenv("RATELIMIT_PROJECT_FORM", "5 per minute")

    @classmethod
    def as_flask_config(cls) -> dict:
        return {
            "RATELIMIT_ENABLED": cls.ENABLED,
            "RATELIMIT_STORAGE_URI": cls.STORAGE_URI,
            "RATELIMIT_DEFAULT_LIMITS": list(cls.DEFAULT_LIMITS),
            "RATELIMIT_TRUST_PROXY": cls.TRUST_PROXY,
            "RATELIMIT_PROXY_X_FOR": cls.PROXY_X_FOR,
            "RATELIMIT_PROXY_X_PROTO": cls.PROXY_X_PROTO,
            "RATELIMIT_PROXY_X_HOST": cls.PROXY_X_HOST,
            "RATELIMIT_AUTH_LOGIN": cls.AUTH_LOGIN,
            "RATELIMIT_ADMIN_LOGIN": cls.ADMIN_LOGIN,
            "RATELIMIT_BOOKING_CREATE": cls.BOOKING_CREATE,
            "RATELIMIT_BOOKING_API": cls.BOOKING_API,
            "RATELIMIT_FORM_SUBMIT": cls.FORM_SUBMIT,
            "RATELIMIT_CHAT_API": cls.CHAT_API,
            "RATELIMIT_PAYMENT": cls.PAYMENT,
        }
