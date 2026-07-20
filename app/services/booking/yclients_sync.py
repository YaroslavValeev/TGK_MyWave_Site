"""YCLIENTS → Google Calendar sync (webhook primary, cron fallback)."""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.config.yclients_config import is_yclients_enabled
from app.services.booking.providers.yclients import YclientsNotConfiguredError

logger = logging.getLogger(__name__)


def sync_record_to_calendar(record: Dict[str, Any]) -> Dict[str, Any]:
    """Upsert one YCLIENTS record into Google Calendar (idempotent by record id)."""
    if not is_yclients_enabled():
        raise YclientsNotConfiguredError("yclients_disabled")

    company_id = str(record.get("company_id") or "")
    record_id = str(record.get("record_id") or record.get("id") or "")
    if not record_id:
        raise ValueError("yclients_record_id_required")

    # Full Calendar mirror implementation ships with credentials + smoke test.
    logger.info(
        "yclients_sync_record_stub",
        extra={
            "company_id": company_id,
            "record_id_tail": record_id[-6:],
            "status": record.get("status"),
        },
    )
    return {
        "status": "stub",
        "company_id": company_id,
        "record_id": record_id,
        "calendar_event_id": None,
    }


def handle_webhook_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Process webhook body; idempotent upsert by company_id + record_id."""
    resource = payload.get("resource") or payload.get("data") or payload
    if not isinstance(resource, dict):
        raise ValueError("invalid_yclients_webhook_payload")
    return sync_record_to_calendar(resource)
