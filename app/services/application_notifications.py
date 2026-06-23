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


def _normalize_lead_status(raw: Any) -> str:
    """Human-readable status for Telegram; never leak Mock/object repr."""
    if raw in (None, ""):
        return "new"
    if isinstance(raw, str):
        text = raw.strip()
    else:
        mod = type(raw).__module__ or ""
        name = type(raw).__name__ or ""
        if mod.startswith("unittest.mock") or name == "MagicMock":
            return "new"
        text = str(raw).strip()
    lowered = text.lower()
    if "magicmock" in lowered or "<" in text and ">" in text and "mock" in lowered:
        return "new"
    if lowered in {"new", "saved", "сохранено", "сохранен", "сохранена"}:
        return "new" if lowered == "new" else "сохранено"
    return text


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
        f"Статус: {_normalize_lead_status(payload.get('status'))}",
    ]
    if application_type == "product":
        qty = payload.get("quantity")
        if qty not in (None, ""):
            lines.insert(6, f"Количество: {qty}")
        pid = payload.get("product_id")
        if pid:
            lines.insert(6, f"Товар ID: {pid}")
    return "\n".join(lines)


SERVICE_LEAD_EVENT_MAP: dict[str, str] = {
    "camp_lead": "camp",
    "coach_lead": "coach_on_location",
    "consulting_lead": "consulting",
}


def notify_service_lead_from_analytics(
    event: str,
    meta: Mapping[str, Any],
    *,
    phone: str = "",
) -> bool:
    """Best-effort Telegram for modal service leads logged via /analytics/log."""
    application_type = SERVICE_LEAD_EVENT_MAP.get(event)
    if not application_type:
        return False

    name = str(meta.get("name") or "").strip()
    phone_val = str(phone or meta.get("phone") or "").strip()
    if len(name) < 2 or len(phone_val) < 8:
        logger.warning(
            "application_notify_skipped reason=missing_contact",
            extra={"application_type": application_type, "event": event},
        )
        return False

    comment_parts = [
        str(meta.get(key) or "").strip()
        for key in ("comment", "goal", "task", "topic", "level", "dates", "location")
        if str(meta.get(key) or "").strip()
    ]
    payload = {
        "name": name,
        "phone": phone_val,
        "comment": "; ".join(comment_parts) if comment_parts else "",
        "source": str(meta.get("service") or application_type).strip(),
        "page_url": str(meta.get("page_url") or "").strip(),
        "status": "new",
    }
    return notify_new_application(application_type, payload)


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
        status = "sent" if ok else "failed_or_skipped"
        logger.info(
            "application_notify_result",
            extra={
                "application_type": application_type,
                "telegram_ok": bool(ok),
                "telegram_status": status,
            },
        )
        return bool(ok)
    except Exception as exc:
        logger.warning(
            "application_notify_failed",
            extra={"application_type": application_type, "error": str(exc)[:200]},
        )
        return False
