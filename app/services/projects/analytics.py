"""
Утилиты для сбора аналитических данных о пользователях.
"""

from flask import request
from typing import Dict, Any, Optional
import re


def get_client_ip() -> str:
    """Получает IP адрес клиента."""
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    elif request.headers.get("X-Real-IP"):
        return request.headers.get("X-Real-IP")
    else:
        return request.remote_addr or "unknown"


def get_user_agent() -> str:
    """Получает User-Agent браузера."""
    return request.headers.get("User-Agent", "unknown")[:500]  # Ограничиваем длину


def get_referrer() -> str:
    """Получает referrer (источник перехода)."""
    return request.headers.get("Referer", "")[:500] or "direct"


def detect_device_type(user_agent: str) -> str:
    """Определяет тип устройства по User-Agent."""
    ua_lower = user_agent.lower()
    if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
        return "mobile"
    elif "tablet" in ua_lower or "ipad" in ua_lower:
        return "tablet"
    else:
        return "desktop"


def detect_browser(user_agent: str) -> str:
    """Определяет браузер по User-Agent."""
    ua_lower = user_agent.lower()
    if "chrome" in ua_lower and "edg" not in ua_lower:
        return "Chrome"
    elif "firefox" in ua_lower:
        return "Firefox"
    elif "safari" in ua_lower and "chrome" not in ua_lower:
        return "Safari"
    elif "edg" in ua_lower:
        return "Edge"
    elif "opera" in ua_lower or "opr" in ua_lower:
        return "Opera"
    else:
        return "Other"


def extract_utm_params() -> Dict[str, str]:
    """Извлекает UTM параметры из URL."""
    utm_params = {}
    for key in ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"]:
        value = request.args.get(key, "")
        if value:
            utm_params[key] = value[:200]  # Ограничиваем длину
    return utm_params


def get_session_data() -> Dict[str, Any]:
    """
    Собирает все доступные аналитические данные о сессии пользователя.

    Returns:
        Словарь с аналитическими данными
    """
    user_agent = get_user_agent()
    utm_params = extract_utm_params()

    return {
        "ip_address": get_client_ip(),
        "user_agent": user_agent,
        "device_type": detect_device_type(user_agent),
        "browser": detect_browser(user_agent),
        "referrer": get_referrer(),
        "utm_source": utm_params.get("utm_source", ""),
        "utm_medium": utm_params.get("utm_medium", ""),
        "utm_campaign": utm_params.get("utm_campaign", ""),
        "utm_term": utm_params.get("utm_term", ""),
        "utm_content": utm_params.get("utm_content", ""),
        "page_url": request.url[:500],
    }
