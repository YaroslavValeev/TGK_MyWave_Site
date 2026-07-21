"""
MyWave Online Coaching — T-Bank (Tinkoff Acquiring) API integration.

Phase 2: Init payment + notification webhook. Manual URL flow remains fallback.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from typing import Any, Dict, Mapping, Optional

import requests
from flask import current_app, has_app_context

from app.modules.logger import get_logger
from app.services.online_coaching_payments import mark_paid, record_manual_payment_url
from app.services.online_coaching_schema import SERVICE_PRICES, format_service_price, service_display_name
from app.services.online_coaching_store import find_request_by_id

logger = get_logger(__name__)

TBANK_API_URL_DEFAULT = "https://securepay.tinkoff.ru/v2"
TBANK_SUCCESS_STATUSES = frozenset({"CONFIRMED", "AUTHORIZED"})


def _cfg(key: str, default: str = "") -> str:
    if has_app_context():
        val = current_app.config.get(key)
        if val not in (None, ""):
            return str(val)
    return str(os.getenv(key, default) or "")


def tbank_terminal_key() -> str:
    return _cfg("TBANK_TERMINAL_KEY")


def tbank_secret_key() -> str:
    return _cfg("TBANK_SECRET_KEY")


def tbank_api_url() -> str:
    return _cfg("TBANK_API_URL", TBANK_API_URL_DEFAULT).rstrip("/")


def is_tbank_configured() -> bool:
    return bool(tbank_terminal_key() and tbank_secret_key())


def build_tbank_token(params: Mapping[str, Any], password: str) -> str:
    """T-Bank token: SHA-256 of sorted scalar values + Password."""
    values: Dict[str, str] = {}
    for key, raw in params.items():
        if key == "Token":
            continue
        if isinstance(raw, (dict, list, tuple)):
            continue
        values[key] = str(raw)
    values["Password"] = password
    concat = "".join(values[k] for k in sorted(values.keys()))
    return hashlib.sha256(concat.encode("utf-8")).hexdigest()


def verify_notification_token(payload: Mapping[str, Any]) -> bool:
    if not is_tbank_configured():
        return False
    expected = build_tbank_token(payload, tbank_secret_key())
    received = str(payload.get("Token") or "")
    return bool(received) and received.lower() == expected.lower()


def _amount_kopecks(service_type: str, amount: Optional[float] = None) -> int:
    if amount is not None:
        return int(round(float(amount) * 100))
    return int(SERVICE_PRICES.get(service_type, 0) * 100)


def init_tbank_payment(
    online_request_id: str,
    *,
    amount: Optional[float] = None,
    return_url: str = "",
    notification_url: str = "",
    sheet_records=None,
    sheet_append=None,
    sheet_update=None,
) -> Dict[str, Any]:
    """Create T-Bank payment and persist link in Sheets."""
    if not is_tbank_configured():
        raise RuntimeError("tbank_not_configured")

    _row_number, record = find_request_by_id(online_request_id, sheet_records=sheet_records)
    if record is None:
        raise ValueError("request_not_found")

    service_type = str(record.get("service_type") or "").strip().lower()
    order_id = f"oc_{online_request_id}_{uuid.uuid4().hex[:8]}"
    amount_kopecks = _amount_kopecks(service_type, amount)
    if amount_kopecks <= 0:
        raise ValueError("invalid_amount")

    description = (
        f"MyWave Online Coaching — {service_display_name(service_type)} "
        f"({format_service_price(service_type)})"
    )
    payload: Dict[str, Any] = {
        "TerminalKey": tbank_terminal_key(),
        "Amount": amount_kopecks,
        "OrderId": order_id,
        "Description": description[:250],
        "DATA": {"online_request_id": online_request_id},
    }
    if return_url:
        payload["SuccessURL"] = return_url
        payload["FailURL"] = return_url
    notify = notification_url or _cfg("TBANK_NOTIFICATION_URL")
    if notify:
        payload["NotificationURL"] = notify

    payload["Token"] = build_tbank_token(payload, tbank_secret_key())

    response = requests.post(
        f"{tbank_api_url()}/Init",
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    body = response.json()
    if not body.get("Success"):
        raise RuntimeError(f"tbank_init_failed:{body.get('ErrorCode')}:{body.get('Message')}")

    payment_url = str(body.get("PaymentURL") or "").strip()
    payment_id = str(body.get("PaymentId") or "")
    if not payment_url:
        raise RuntimeError("tbank_init_missing_payment_url")

    result = record_manual_payment_url(
        online_request_id,
        payment_url,
        amount=amount_kopecks / 100.0,
        tbank_order_id=order_id,
        sheet_append=sheet_append,
        sheet_records=sheet_records,
        sheet_update=sheet_update,
    )
    result["tbank_order_id"] = order_id
    result["tbank_payment_id"] = payment_id
    logger.info(
        "online_coaching_tbank_init",
        extra={
            "online_request_id": online_request_id,
            "tbank_order_id": order_id,
            "tbank_payment_id": payment_id,
        },
    )
    return result


def extract_online_request_id(payload: Mapping[str, Any]) -> str:
    data = payload.get("DATA")
    if isinstance(data, dict):
        req_id = str(data.get("online_request_id") or "").strip()
        if req_id:
            return req_id
    order_id = str(payload.get("OrderId") or "")
    if order_id.startswith("oc_oc_req_"):
        return order_id[3:].rsplit("_", 1)[0]
    if order_id.startswith("oc_"):
        return order_id[3:].rsplit("_", 1)[0]
    return ""


def handle_tbank_notification(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Process T-Bank webhook; mark paid on CONFIRMED/AUTHORIZED."""
    if not verify_notification_token(payload):
        raise ValueError("invalid_tbank_token")

    status = str(payload.get("Status") or "").upper()
    online_request_id = extract_online_request_id(payload)
    order_id = str(payload.get("OrderId") or "")

    logger.info(
        "online_coaching_tbank_webhook",
        extra={
            "online_request_id": online_request_id or None,
            "status": status,
            "order_id": order_id or None,
        },
    )

    if status not in TBANK_SUCCESS_STATUSES:
        return {"ack": True, "action": "ignored", "status": status}

    if not online_request_id:
        raise ValueError("online_request_id_missing")

    amount_raw = payload.get("Amount")
    amount = float(amount_raw) / 100.0 if amount_raw is not None else None
    result = mark_paid(online_request_id, amount=amount)
    return {"ack": True, "action": "mark_paid", "online_request_id": online_request_id, "result": result}
