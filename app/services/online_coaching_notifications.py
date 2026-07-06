"""
Telegram notifications for MyWave Online Coaching.

MVP rules:
- URL buttons open admin UI only (no GET status changes).
- No full PII/health data in Telegram — see sanitize_record_for_telegram().
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, Mapping, Optional

from flask import current_app, has_app_context

from app.services.notifications import send_telegram_notification_with_keyboard
from app.services.online_coaching_schema import PROGRESS_MONTH_MAX_SESSIONS, SERVICE_PRICES, service_display_name

logger = logging.getLogger(__name__)

_PHONE_MASK_RE = re.compile(r"\D+")


def _cfg(key: str, default: str = "") -> str:
    if has_app_context():
        val = current_app.config.get(key)
        if val not in (None, ""):
            return str(val)
    return str(os.getenv(key, default) or "")


def _public_base_url() -> str:
    return (
        _cfg("SITE_BASE_URL")
        or _cfg("PUBLIC_BASE_URL")
        or _cfg("BASE_URL")
        or "https://mywavewake.ru"
    ).rstrip("/")


def admin_detail_url(online_request_id: str) -> str:
    return f"{_public_base_url()}/admin/online-coaching/{online_request_id}"


def _service_label(service_type: str) -> str:
    return service_display_name(service_type)


def _mask_phone(phone: str) -> str:
    digits = _PHONE_MASK_RE.sub("", phone or "")
    if len(digits) < 4:
        return "—"
    return f"***{digits[-4:]}"


def _health_limits_label(record: Mapping[str, Any]) -> str:
    raw = str(record.get("injuries_or_limits") or record.get("has_injuries_info") or "").strip()
    if raw.lower() in {"yes", "1", "true"}:
        return "указаны"
    if raw:
        return "указаны"
    return "не указаны"


def sanitize_record_for_telegram(record: Mapping[str, Any]) -> Dict[str, str]:
    """Strip sensitive fields before Telegram notify."""
    contact = ""
    channel = str(record.get("preferred_channel") or "").lower()
    if channel == "telegram":
        contact = str(record.get("telegram_username") or "")[:80]
    elif channel == "email":
        email = str(record.get("email") or "")
        if "@" in email:
            local, _, domain = email.partition("@")
            contact = f"{local[:2]}***@{domain}" if local else email
    return {
        "online_request_id": str(record.get("online_request_id") or ""),
        "name": str(record.get("name") or "—")[:80],
        "phone_masked": _mask_phone(str(record.get("phone") or "")),
        "preferred_channel": str(record.get("preferred_channel") or "—"),
        "contact_hint": contact or "—",
        "service_type": str(record.get("service_type") or ""),
        "discipline": str(record.get("discipline") or "—"),
        "level": str(record.get("level") or "—"),
        "goal_short": (str(record.get("goal") or "—"))[:60],
        "health_limits": _health_limits_label(record),
        "video_flag": "ссылка есть" if str(record.get("video_url") or "").strip() else "ссылки нет",
        "request_status": str(record.get("request_status") or "new"),
        "payment_required_timing": str(record.get("payment_required_timing") or ""),
        "deadline_at": str(record.get("deadline_at") or "—"),
        "created_at": str(record.get("created_at") or ""),
    }


def _inline_open_admin_only(online_request_id: str) -> list:
    """Telegram URL buttons — admin UI only, no action query params."""
    return [[{"text": "Открыть заявку", "url": admin_detail_url(online_request_id)}]]


def format_new_request_message(record: Mapping[str, Any]) -> str:
    safe = sanitize_record_for_telegram(record)
    timing = safe["payment_required_timing"] or "—"
    pay_hint = "требуется сейчас" if timing == "upfront" else "после услуги"
    return (
        "Новая заявка MyWave Online Coaching\n\n"
        f"Формат: {_service_label(safe['service_type'])}\n"
        f"Имя: {safe['name']}\n"
        f"Телефон: {safe['phone_masked']}\n"
        f"Канал связи: {safe['preferred_channel']}\n"
        f"Контакт: {safe['contact_hint']}\n"
        f"Дисциплина: {safe['discipline']}\n"
        f"Уровень: {safe['level']}\n"
        f"Цель: {safe['goal_short']}\n"
        f"Ограничения по здоровью: {safe['health_limits']}\n"
        f"Видео: {safe['video_flag']}\n"
        f"Оплата: {pay_hint}\n"
        f"Статус: {safe['request_status']}\n"
        f"ID: {safe['online_request_id']}"
    )


def format_video_received_message(record: Mapping[str, Any]) -> str:
    safe = sanitize_record_for_telegram(record)
    return (
        "Видео получено\n\n"
        f"Клиент: {safe['name']}\n"
        f"Услуга: {_service_label(safe['service_type'])}\n"
        f"Видео: {safe['video_flag']}\n"
        f"Дедлайн разбора: {safe['deadline_at']}\n"
        f"ID: {safe['online_request_id']}"
    )


def format_review_ready_message(record: Mapping[str, Any]) -> str:
    safe = sanitize_record_for_telegram(record)
    return (
        "Разбор готов\n\n"
        f"Клиент: {safe['name']}\n"
        f"Услуга: {_service_label(safe['service_type'])}\n"
        f"Статус: review_ready\n"
        f"ID: {safe['online_request_id']}\n\n"
        "Отправьте разбор клиенту, затем смените статус в admin UI."
    )


def format_review_sent_message(record: Mapping[str, Any]) -> str:
    safe = sanitize_record_for_telegram(record)
    service_type = safe["service_type"]
    timing = safe["payment_required_timing"]
    extra = ""
    if timing == "after_service" or service_type in ("video_check", "live_coach_land", "live_coach_water"):
        extra = "\nПосле подтверждения — отправьте ссылку Т-Банка (admin UI)."
    return (
        "Разбор отправлен клиенту\n\n"
        f"Клиент: {safe['name']}\n"
        f"Услуга: {_service_label(service_type)}\n"
        f"ID: {safe['online_request_id']}"
        f"{extra}"
    )


def format_payment_needed_message(record: Mapping[str, Any], amount: Optional[float] = None) -> str:
    safe = sanitize_record_for_telegram(record)
    service_type = safe["service_type"]
    price = amount if amount is not None else SERVICE_PRICES.get(service_type, 0)
    return (
        "Нужно отправить ссылку Т-Банка на оплату\n\n"
        f"Клиент: {safe['name']}\n"
        f"Услуга: {_service_label(service_type)}\n"
        f"Сумма: {int(price)} ₽\n"
        f"ID: {safe['online_request_id']}"
    )


def format_subscription_paid_message(record: Mapping[str, Any], *, period_end: str = "") -> str:
    safe = sanitize_record_for_telegram(record)
    return (
        "Подписка «Эффективный месяц» активирована\n\n"
        f"Клиент: {safe['name']}\n"
        f"Период: {safe['created_at'][:10] if safe['created_at'] else '—'} — {period_end or '—'}\n"
        "Статус: subscription_active\n"
        f"Лимит: до {PROGRESS_MONTH_MAX_SESSIONS} тренировок/месяц\n"
        f"Канал связи: {safe['preferred_channel']}\n"
        f"ID: {safe['online_request_id']}"
    )


def format_client_message_notification(record: Mapping[str, Any], *, message_preview: str = "") -> str:
    safe = sanitize_record_for_telegram(record)
    preview = (message_preview or "—")[:120]
    return (
        "Новое сообщение по онлайн-услуге\n\n"
        f"Клиент: {safe['name']}\n"
        f"Услуга: {_service_label(safe['service_type'])}\n"
        f"Сообщение: {preview}\n"
        f"ID: {safe['online_request_id']}"
    )


def _send(text: str, keyboard: list, *, event: str, req_id: str) -> bool:
    try:
        ok = bool(send_telegram_notification_with_keyboard(text, keyboard))
        logger.info("online_coaching_telegram_notify event=%s id=%s ok=%s", event, req_id, ok)
        return ok
    except Exception as exc:
        logger.warning("online_coaching_telegram_notify_failed event=%s id=%s err=%s", event, req_id, str(exc)[:200])
        return False


def notify_new_online_request(record: Mapping[str, Any]) -> bool:
    req_id = str(record.get("online_request_id") or "")
    return _send(format_new_request_message(record), _inline_open_admin_only(req_id), event="new_request", req_id=req_id)


def notify_video_received(record: Mapping[str, Any]) -> bool:
    req_id = str(record.get("online_request_id") or "")
    return _send(format_video_received_message(record), _inline_open_admin_only(req_id), event="video_received", req_id=req_id)


def notify_review_ready(record: Mapping[str, Any]) -> bool:
    req_id = str(record.get("online_request_id") or "")
    return _send(format_review_ready_message(record), _inline_open_admin_only(req_id), event="review_ready", req_id=req_id)


def notify_review_sent(record: Mapping[str, Any]) -> bool:
    req_id = str(record.get("online_request_id") or "")
    return _send(format_review_sent_message(record), _inline_open_admin_only(req_id), event="review_sent", req_id=req_id)


def notify_payment_needed(record: Mapping[str, Any], amount: Optional[float] = None) -> bool:
    req_id = str(record.get("online_request_id") or "")
    return _send(
        format_payment_needed_message(record, amount),
        _inline_open_admin_only(req_id),
        event="payment_needed",
        req_id=req_id,
    )


def notify_subscription_paid(record: Mapping[str, Any], *, period_end: str = "") -> bool:
    req_id = str(record.get("online_request_id") or "")
    return _send(
        format_subscription_paid_message(record, period_end=period_end),
        _inline_open_admin_only(req_id),
        event="subscription_active",
        req_id=req_id,
    )


def notify_client_message(record: Mapping[str, Any], *, message_preview: str = "") -> bool:
    req_id = str(record.get("online_request_id") or "")
    return _send(
        format_client_message_notification(record, message_preview=message_preview),
        _inline_open_admin_only(req_id),
        event="client_message",
        req_id=req_id,
    )
