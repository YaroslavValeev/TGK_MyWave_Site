"""
Unified Telegram notifications for site application leads (PR53 foundation).

Best-effort: Telegram failure must not break the caller's primary flow.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Mapping

from app.services.notifications import send_telegram_notification

logger = logging.getLogger(__name__)

APPLICATION_TYPE_LABELS: dict[str, str] = {
    "product": "Заявка на товар",
    "wake_challenge": "Wake Challenge",
    "wakesurf_safari": "WakeSurf Safari",
    "ruza_camp": "MyWave Ruza Camp",
    "camp": "MyWave Camp",
    "coach_on_location": "Тренер на выезде",
    "consulting": "Консультация",
    "social": "MyWave Social",
    "generic_project": "Проектная заявка",
}


def _format_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _pick(payload: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        val = payload.get(key)
        if val not in (None, ""):
            return str(val).strip()
    return "—"


def format_application_telegram_message(application_type: str, payload: Mapping[str, Any]) -> str:
    """Build admin Telegram text from normalized payload."""
    title = APPLICATION_TYPE_LABELS.get(application_type, application_type)
    lines = [
        f"Новая заявка: {title}",
        "",
        f"Имя: {_pick(payload, 'name', 'parent_name', 'full_name')}",
        f"Телефон: {_pick(payload, 'phone', 'parent_phone')}",
        f"Telegram: {_pick(payload, 'telegram', 'telegram_username')}",
        f"Email: {_pick(payload, 'email', 'parent_email')}",
        f"Проект/услуга: {_pick(payload, 'product_title', 'project', 'service', 'desired_format')}",
        f"Комментарий: {_pick(payload, 'comment', 'motivation_text', 'safety_notes')}",
        f"Источник: {_pick(payload, 'source')}",
        f"Страница: {_pick(payload, 'page_url')}",
        f"Время: {_pick(payload, 'created_at') or _format_timestamp()}",
        "",
        f"Статус: {_pick(payload, 'status') or 'new'}",
    ]
    if application_type == "product":
        qty = payload.get("quantity")
        if qty not in (None, ""):
            lines.insert(6, f"Количество: {qty}")
        pid = payload.get("product_id")
        if pid:
            lines.insert(6, f"Товар ID: {pid}")
    return "\n".join(lines)


def notify_new_application(application_type: str, payload: Mapping[str, Any]) -> bool:
    """
    Send Telegram notification for a new application lead.
    Returns True if Telegram accepted the message, False otherwise.
    """
    if application_type not in APPLICATION_TYPE_LABELS:
        logger.warning(
            "application_notify_unknown_type",
            extra={"application_type": application_type},
        )

    message = format_application_telegram_message(application_type, payload)
    name = _pick(payload, "name", "parent_name", "full_name") or "Заявка"
    phone = _pick(payload, "phone", "parent_phone")

    try:
        ok = send_telegram_notification(name, phone, message)
        logger.info(
            "application_notify_result",
            extra={
                "application_type": application_type,
                "telegram_ok": bool(ok),
            },
        )
        return bool(ok)
    except Exception as exc:
        logger.warning(
            "application_notify_failed",
            extra={"application_type": application_type, "error": str(exc)[:200]},
        )
        return False
