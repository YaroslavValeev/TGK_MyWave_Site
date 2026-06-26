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


def _sanitize_notify_value(raw: Any) -> str:
    """Strip mock/object repr from Telegram payload fields."""
    if raw in (None, ""):
        return ""
    if isinstance(raw, str):
        text = raw.strip()
    else:
        mod = type(raw).__module__ or ""
        name = type(raw).__name__ or ""
        if mod.startswith("unittest.mock") or name == "MagicMock":
            return ""
        text = str(raw).strip()
    lowered = text.lower()
    if "magicmock" in lowered:
        return ""
    if "<" in text and ">" in text and "mock" in lowered:
        return ""
    return text


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


def format_social_telegram_message(payload: Mapping[str, Any]) -> str:
    """Sanitized Telegram for Social applications — no health_notes / medical details."""
    app_id = _sanitize_notify_value(payload.get("application_id"))
    name = _sanitize_notify_value(_pick(payload, "parent_name", "name")) or "—"
    phone = _sanitize_notify_value(_pick(payload, "parent_phone", "phone"))
    telegram = _sanitize_notify_value(_pick(payload, "telegram_username", "telegram"))
    age = _sanitize_notify_value(payload.get("child_age"))
    city = _sanitize_notify_value(payload.get("city"))
    page_url = _sanitize_notify_value(_pick(payload, "page_url")) or "—"

    has_safety = payload.get("has_safety_info")
    if isinstance(has_safety, bool):
        safety_label = "да" if has_safety else "нет"
    else:
        safety_label = _sanitize_notify_value(has_safety) or "нет"

    lines = ["Новая заявка: MyWave Social", ""]
    if app_id:
        lines.append(f"ID: {app_id}")
    lines.append(f"Имя: {name}")
    if phone:
        lines.append(f"Телефон: {phone}")
    if telegram:
        lines.append(f"Telegram: {telegram}")
    if age:
        lines.append(f"Возраст: {age}")
    if city:
        lines.append(f"Город: {city}")
    lines.extend(
        [
            f"Важная информация для безопасности: {safety_label}",
            f"Страница: {page_url}",
            f"Статус: {_normalize_lead_status(payload.get('status'))}",
        ]
    )
    return "\n".join(lines)


def format_social_session_scheduled_message(payload: Mapping[str, Any]) -> str:
    """Sanitized Telegram for manual session assign — no health / PII beyond IDs."""
    app_id = _sanitize_notify_value(payload.get("application_id"))
    sess_id = _sanitize_notify_value(payload.get("session_id"))
    session_date = _sanitize_notify_value(payload.get("session_date"))
    session_time = _sanitize_notify_value(payload.get("session_time"))
    location = _sanitize_notify_value(payload.get("location")) or "—"
    status = _normalize_lead_status(payload.get("status")) or "scheduled"

    lines = ["Social session scheduled", ""]
    if app_id:
        lines.append(f"application_id: {app_id}")
    if sess_id:
        lines.append(f"session_id: {sess_id}")
    if session_date:
        lines.append(f"Дата: {session_date}")
    if session_time:
        lines.append(f"Время: {session_time}")
    lines.append(f"Локация: {location}")
    lines.append(f"status={status}")
    return "\n".join(lines)


def notify_social_session_scheduled(payload: Mapping[str, Any]) -> bool:
    """Best-effort Telegram after manual social session assign."""
    message = format_social_session_scheduled_message(payload)
    app_id = _sanitize_notify_value(payload.get("application_id")) or "Social session"
    try:
        ok = send_telegram_notification(app_id, "", message)
        logger.info(
            "social_session_notify_result",
            extra={
                "application_id": app_id,
                "session_id": _sanitize_notify_value(payload.get("session_id")),
                "telegram_ok": bool(ok),
            },
        )
        return bool(ok)
    except Exception as exc:
        logger.warning(
            "social_session_notify_failed",
            extra={"error": str(exc)[:200]},
        )
        return False


def format_application_telegram_message(application_type: str, payload: Mapping[str, Any]) -> str:
    """Build admin Telegram text from normalized payload."""
    if application_type == "social":
        return format_social_telegram_message(payload)

    title = APPLICATION_TYPE_LABELS.get(application_type, application_type)
    name = _sanitize_notify_value(_pick(payload, "name", "parent_name", "full_name")) or "—"
    phone = _sanitize_notify_value(_pick(payload, "phone", "parent_phone")) or "—"
    telegram = _sanitize_notify_value(_pick(payload, "telegram", "telegram_username")) or "—"
    email = _sanitize_notify_value(_pick(payload, "email", "parent_email")) or "—"
    comment_raw = _sanitize_notify_value(
        _pick(payload, "comment", "motivation_text")
    )
    if not comment_raw:
        comment_raw = "—"
    elif len(comment_raw) > 200:
        comment_raw = comment_raw[:200] + "…"
    page_url = _sanitize_notify_value(_pick(payload, "page_url")) or "—"
    source = _sanitize_notify_value(_pick(payload, "source")) or "—"
    app_id = _sanitize_notify_value(payload.get("application_id"))

    lines = [
        f"Новая заявка: {title}",
        "",
    ]
    if app_id:
        lines.append(f"ID: {app_id}")
    lines.extend([
        f"Тип: {application_type}",
        f"Имя: {name}",
        f"Телефон: {phone}",
        f"Telegram: {telegram}",
    ])
    if email != "—":
        lines.append(f"Email: {email}")
    lines.extend([
        f"Комментарий: {comment_raw}",
        f"Источник: {source}",
        f"Страница: {page_url}",
        f"Статус: {_normalize_lead_status(payload.get('status'))}",
    ])
    if application_type == "product":
        qty = payload.get("quantity")
        if qty not in (None, ""):
            qty_text = _sanitize_notify_value(qty)
            if qty_text:
                lines.insert(-1, f"Количество: {qty_text}")
        pid = _sanitize_notify_value(payload.get("product_id"))
        if pid:
            lines.insert(-1, f"Товар ID: {pid}")
        product_title = _sanitize_notify_value(payload.get("product_title"))
        if product_title:
            lines.insert(-1, f"Товар: {product_title}")
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
    """Best-effort Project_Applications + Telegram for modal service leads via /analytics/log."""
    from app.services.project_applications import try_submit_from_analytics_event

    result = try_submit_from_analytics_event(event, meta, phone=phone)
    if result is None:
        return False
    return result.notification_status == "sent"


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
