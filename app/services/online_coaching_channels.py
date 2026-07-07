"""
MyWave Online Coaching — outbound notifications for WhatsApp / MAX channels.

Phase 2: HTTP webhook adapters (credentials via env). Telegram remains primary for trainer.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Mapping, Optional

import requests
from flask import current_app, has_app_context

from app.modules.logger import get_logger
from app.services.online_coaching_schema import service_display_name

logger = get_logger(__name__)


def _cfg(key: str, default: str = "") -> str:
    if has_app_context():
        val = current_app.config.get(key)
        if val not in (None, ""):
            return str(val)
    return str(os.getenv(key, default) or "")


def is_max_configured() -> bool:
    return bool(_cfg("MAX_API_URL") and _cfg("MAX_API_TOKEN"))


def is_whatsapp_configured() -> bool:
    return bool(_cfg("WHATSAPP_API_URL") and _cfg("WHATSAPP_API_TOKEN"))


def _recipient_for_channel(record: Mapping[str, Any], channel: str) -> str:
    if channel == "max":
        return str(record.get("max_contact") or "").strip()
    if channel == "whatsapp":
        return str(record.get("whatsapp_phone") or "").strip()
    if channel == "telegram":
        return str(record.get("telegram_username") or "").strip()
    if channel == "email":
        return str(record.get("email") or "").strip()
    return str(record.get("phone") or "").strip()


def send_max_message(recipient: str, text: str, *, timeout: int = 20) -> bool:
    api_url = _cfg("MAX_API_URL")
    token = _cfg("MAX_API_TOKEN")
    if not api_url or not token or not recipient:
        logger.info("online_coaching_max_skipped reason=missing_config_or_recipient")
        return False
    payload = {
        "recipient": recipient,
        "text": text[:4000],
        "source": "mywave_online_coaching",
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post(api_url, json=payload, headers=headers, timeout=timeout)
    ok = 200 <= response.status_code < 300
    logger.info(
        "online_coaching_max_send",
        extra={"recipient_hint": recipient[:4] + "***", "ok": ok, "status": response.status_code},
    )
    return ok


def send_whatsapp_message(recipient: str, text: str, *, timeout: int = 20) -> bool:
    api_url = _cfg("WHATSAPP_API_URL")
    token = _cfg("WHATSAPP_API_TOKEN")
    if not api_url or not token or not recipient:
        logger.info("online_coaching_whatsapp_skipped reason=missing_config_or_recipient")
        return False
    payload = {
        "to": recipient,
        "body": text[:4000],
        "source": "mywave_online_coaching",
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post(api_url, json=payload, headers=headers, timeout=timeout)
    ok = 200 <= response.status_code < 300
    logger.info(
        "online_coaching_whatsapp_send",
        extra={"recipient_hint": recipient[:4] + "***", "ok": ok, "status": response.status_code},
    )
    return ok


def format_client_status_message(record: Mapping[str, Any], *, event: str) -> str:
    name = str(record.get("name") or "клиент")[:80]
    service = service_display_name(str(record.get("service_type") or ""))
    req_id = str(record.get("online_request_id") or "")
    status = str(record.get("request_status") or "")

    if event == "application_received":
        return (
            f"Здравствуйте, {name}! Заявка MyWave Online Coaching принята.\n"
            f"Услуга: {service}\n"
            f"Номер заявки: {req_id}\n"
            "Мы свяжемся с вами в ближайшее время."
        )
    if event == "video_received":
        return (
            f"{name}, ваше видео по заявке {req_id} получено.\n"
            f"Статус: {status}. Тренер приступит к разбору в срок до 48 часов."
        )
    if event == "payment_link":
        url = str(record.get("tbank_payment_url") or "").strip()
        extra = f"\nСсылка на оплату: {url}" if url else ""
        return f"{name}, для оплаты услуги «{service}» перейдите по ссылке.{extra}"
    return f"MyWave Online Coaching — обновление по заявке {req_id}. Статус: {status}."


def notify_client_channel(
    record: Mapping[str, Any],
    *,
    event: str,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """Send client-facing notification via preferred channel when API is configured."""
    channel = str(record.get("preferred_channel") or "").strip().lower()
    recipient = _recipient_for_channel(record, channel)
    text = message or format_client_status_message(record, event=event)
    result: Dict[str, Any] = {"channel": channel, "sent": False, "skipped": True}

    if channel == "max" and is_max_configured():
        result["sent"] = send_max_message(recipient, text)
        result["skipped"] = not result["sent"]
    elif channel == "whatsapp" and is_whatsapp_configured():
        result["sent"] = send_whatsapp_message(recipient, text)
        result["skipped"] = not result["sent"]
    else:
        logger.info(
            "online_coaching_channel_notify_skipped",
            extra={
                "online_request_id": record.get("online_request_id"),
                "channel": channel,
                "event": event,
            },
        )

    return result
