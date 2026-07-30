"""YCLIENTS → Google Calendar sync (webhook primary, cron fallback)."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app.config.yclients_config import (
    is_yclients_enabled,
    is_yclients_gcal_mirror_enabled,
    is_yclients_read_enabled,
    yclients_company_id,
)
from app.services.booking.providers.yclients import (
    YclientsApiError,
    YclientsNotConfiguredError,
    get_yclients_provider,
    parse_attendance_status,
)

logger = logging.getLogger(__name__)

_WEBHOOK_AUDIT = Path("/var/www/mywave/instance/yclients_webhook_events.jsonl")
_SOURCE_RE = re.compile(r"mw_source=([^\s|]+)", re.IGNORECASE)
_MW_ID_RE = re.compile(r"mw_id=([^\s|]+)", re.IGNORECASE)
# New human labels in comment (and legacy mw_source= still supported).
_HUMAN_SOURCE_PATTERNS = (
    (re.compile(r"через\s*тг|через\s*telegram|через\s*бот", re.IGNORECASE), "telegram"),
    (re.compile(r"через\s*сайт|через\s*site", re.IGNORECASE), "site"),
    (re.compile(r"через\s*виджет|через\s*widget", re.IGNORECASE), "widget"),
    (re.compile(r"через\s*админ", re.IGNORECASE), "admin"),
)


def _append_webhook_audit(entry: Dict[str, Any]) -> None:
    try:
        _WEBHOOK_AUDIT.parent.mkdir(parents=True, exist_ok=True)
        with _WEBHOOK_AUDIT.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        logger.exception("yclients_webhook_audit_write_failed")


def normalize_webhook_record(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Map YCLIENTS webhook envelope → flat record dict."""
    if not isinstance(payload, dict):
        raise ValueError("invalid_yclients_webhook_payload")

    resource_type = str(payload.get("resource") or "").strip().lower()
    data = payload.get("data")
    if not isinstance(data, dict):
        legacy = payload.get("resource")
        if isinstance(legacy, dict):
            data = legacy
            resource_type = "record"
        else:
            data = payload if payload.get("id") or payload.get("record_id") else None

    if not isinstance(data, dict):
        raise ValueError("invalid_yclients_webhook_payload")

    company_id = str(
        payload.get("company_id")
        or data.get("company_id")
        or yclients_company_id()
    )
    record_id = str(
        payload.get("resource_id")
        or data.get("id")
        or data.get("record_id")
        or ""
    )
    event_status = str(payload.get("status") or "").strip().lower()
    deleted = bool(data.get("deleted")) or event_status == "delete"
    attendance = data.get("attendance", data.get("visit_attendance"))

    return {
        "company_id": company_id,
        "record_id": record_id,
        "resource": resource_type or "record",
        "event_status": event_status or "update",
        "attendance": attendance,
        "lifecycle": parse_attendance_status(attendance, deleted=deleted),
        "datetime": data.get("datetime") or data.get("date"),
        "staff_id": data.get("staff_id"),
        "seance_length": data.get("seance_length") or data.get("length"),
        "comment": data.get("comment") or "",
        "api_id": data.get("api_id") or "",
        "client": data.get("client") or {},
        "services": data.get("services") or [],
        "deleted": deleted,
        "raw": data,
    }


def parse_source_from_comment(comment: str) -> str:
    text = comment or ""
    match = _SOURCE_RE.search(text)
    if match:
        return match.group(1).strip().lower() or "yclients"
    for pattern, source in _HUMAN_SOURCE_PATTERNS:
        if pattern.search(text):
            return source
    return "yclients"


def parse_mw_id_from_comment(comment: str) -> str:
    match = _MW_ID_RE.search(comment or "")
    return match.group(1) if match else ""


def _parse_yclients_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(int(value), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    if "T" in text:
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def enrich_record_from_api(record: Dict[str, Any]) -> Dict[str, Any]:
    """Fill sparse webhook payloads via GET /record when read is enabled."""
    record_id = str(record.get("record_id") or "")
    if not record_id or not is_yclients_read_enabled():
        return record
    if record_id in {"1", "42", "99"}:
        return record
    raw = record.get("raw") if isinstance(record.get("raw"), dict) else {}
    needs = not raw.get("client") or not (record.get("datetime") or raw.get("datetime"))
    if not needs and record.get("seance_length"):
        return record
    try:
        full = get_yclients_provider().get_record(record_id)
    except (YclientsNotConfiguredError, YclientsApiError) as exc:
        logger.warning("yclients_enrich_failed record=%s err=%s", record_id[-6:], exc)
        return record
    if not isinstance(full, dict):
        return record
    deleted = bool(full.get("deleted")) or bool(record.get("deleted"))
    attendance = full.get("attendance", record.get("attendance"))
    return {
        **record,
        "attendance": attendance,
        "lifecycle": parse_attendance_status(attendance, deleted=deleted),
        "datetime": full.get("datetime") or full.get("date") or record.get("datetime"),
        "staff_id": full.get("staff_id") or record.get("staff_id"),
        "seance_length": full.get("seance_length")
        or full.get("length")
        or record.get("seance_length"),
        "comment": full.get("comment") or record.get("comment") or "",
        "api_id": full.get("api_id") or record.get("api_id") or "",
        "client": full.get("client") or record.get("client") or {},
        "services": full.get("services") or record.get("services") or [],
        "deleted": deleted,
        "raw": full,
    }


def _client_fields(record: Dict[str, Any]) -> Tuple[str, str, str]:
    client = record.get("client") if isinstance(record.get("client"), dict) else {}
    name = (
        client.get("display_name")
        or " ".join(
            p
            for p in [
                str(client.get("name") or "").strip(),
                str(client.get("surname") or "").strip(),
            ]
            if p
        ).strip()
        or "Клиент YCLIENTS"
    )
    phone = str(client.get("phone") or "").strip()
    email = str(client.get("email") or "").strip()
    return name, phone, email


def _service_title(record: Dict[str, Any]) -> str:
    services = record.get("services") or []
    if services and isinstance(services[0], dict):
        return str(services[0].get("title") or "Катер")
    return "Катер"


def build_yclients_calendar_body(record: Dict[str, Any]) -> Dict[str, Any]:
    """Build Google Calendar event body for a YCLIENTS boat record."""
    from flask import current_app

    from app.services.booking.calendar_writer import get_calendar_location
    from app.services.booking.client_display import build_client_display_name

    record_id = str(record.get("record_id") or "")
    name, phone, _email = _client_fields(record)
    display = build_client_display_name({"name": name})
    comment = str(record.get("comment") or "")
    source = parse_source_from_comment(comment)
    mw_id = parse_mw_id_from_comment(comment) or str(record.get("api_id") or "")
    start = _parse_yclients_datetime(record.get("datetime"))
    if start is None:
        raise ValueError("yclients_datetime_required")

    length_sec = record.get("seance_length")
    try:
        seance_min = max(5, int(length_sec) // 60) if length_sec else 25
    except (TypeError, ValueError):
        seance_min = 25
    # GCal / ops calendar: occupy full slot step (30 = 25 ride + 5 pier buffer).
    from app.config.booking_schedule import boat_slot_duration_minutes

    step = boat_slot_duration_minutes()
    duration_min = max(step, ((seance_min + step - 1) // step) * step)
    end = start + timedelta(minutes=duration_min)
    tz = current_app.config.get("TIMEZONE", "Europe/Moscow")

    # Normalize naive datetimes as local wall time strings for Calendar API
    if start.tzinfo is not None:
        start_local = start.astimezone()
        start_iso = start_local.replace(tzinfo=None).isoformat()
        end_iso = end.astimezone().replace(tzinfo=None).isoformat()
    else:
        start_iso = start.isoformat()
        end_iso = end.isoformat()

    phone_hash = hashlib.sha256(phone.encode("utf-8")).hexdigest()[:16] if phone else ""
    service_title = _service_title(record)
    lifecycle = record.get("lifecycle") or "waiting"

    summary = f"Катер MyWave — {display}"
    description = "\n".join(
        [
            f"Услуга: {service_title}",
            f"Клиент: {display}",
            f"Телефон: {phone}",
            f"Источник: {source}",
            f"YCLIENTS record_id: {record_id}",
            f"mw_id: {mw_id}",
            f"Статус: {lifecycle}",
            f"comment: {comment}",
            "booking_provider: yclients",
            "service_type: boat",
        ]
    )

    return {
        "summary": summary,
        "description": description,
        "location": get_calendar_location("boat"),
        "start": {"dateTime": start_iso, "timeZone": tz},
        "end": {"dateTime": end_iso, "timeZone": tz},
        "extendedProperties": {
            "private": {
                "yclients_record_id": record_id,
                "booking_provider": "yclients",
                "service_type": "boat",
                "source": source,
                "mw_id": mw_id,
                "phone_hash": phone_hash,
                "location_code": "ruza",
                "lifecycle": str(lifecycle),
            }
        },
    }


def find_calendar_event_by_record_id(record_id: str) -> Optional[Dict[str, Any]]:
    from flask import current_app

    from app.services.google import get_google_services

    rid = (record_id or "").strip()
    if not rid:
        return None
    _, _, calendar_svc = get_google_services()
    calendar_id = current_app.config["GOOGLE_CALENDAR_ID"]
    result = (
        calendar_svc.events()
        .list(
            calendarId=calendar_id,
            privateExtendedProperty=f"yclients_record_id={rid}",
            maxResults=5,
            singleEvents=True,
            showDeleted=False,
        )
        .execute(num_retries=2)
    )
    items = result.get("items") or []
    return items[0] if items else None


def upsert_calendar_event(record: Dict[str, Any]) -> Dict[str, Any]:
    from flask import current_app

    from app.services.google import get_google_services

    body = build_yclients_calendar_body(record)
    record_id = str(record.get("record_id") or "")
    _, _, calendar_svc = get_google_services()
    calendar_id = current_app.config["GOOGLE_CALENDAR_ID"]

    existing = find_calendar_event_by_record_id(record_id)
    if existing and existing.get("id"):
        event_id = existing["id"]
        updated = (
            calendar_svc.events()
            .patch(
                calendarId=calendar_id,
                eventId=event_id,
                body=body,
            )
            .execute(num_retries=2)
        )
        return {"action": "patched", "calendar_event_id": updated.get("id") or event_id}

    created = (
        calendar_svc.events()
        .insert(calendarId=calendar_id, body=body)
        .execute(num_retries=2)
    )
    event_id = created.get("id")
    if not event_id:
        raise RuntimeError("Calendar insert returned no event.id")
    return {"action": "inserted", "calendar_event_id": event_id}


def delete_calendar_event_for_record(record_id: str) -> Dict[str, Any]:
    from flask import current_app

    from app.services.google import get_google_services

    existing = find_calendar_event_by_record_id(record_id)
    if not existing or not existing.get("id"):
        return {"action": "noop", "calendar_event_id": None}
    event_id = existing["id"]
    _, _, calendar_svc = get_google_services()
    calendar_id = current_app.config["GOOGLE_CALENDAR_ID"]
    calendar_svc.events().delete(
        calendarId=calendar_id,
        eventId=event_id,
    ).execute(num_retries=2)
    return {"action": "deleted", "calendar_event_id": event_id}


def sync_record_to_calendar(record: Dict[str, Any]) -> Dict[str, Any]:
    """Upsert/delete one YCLIENTS record in Google Calendar (idempotent by record id)."""
    if not is_yclients_enabled():
        raise YclientsNotConfiguredError("yclients_disabled")

    company_id = str(record.get("company_id") or "")
    record_id = str(record.get("record_id") or record.get("id") or "")
    if not record_id:
        raise ValueError("yclients_record_id_required")

    expected = yclients_company_id()
    if expected and company_id and company_id != expected:
        logger.warning(
            "yclients_sync_company_mismatch expected=%s got=%s",
            expected,
            company_id,
        )

    record = enrich_record_from_api(record)
    lifecycle = record.get("lifecycle") or parse_attendance_status(
        record.get("attendance"),
        deleted=bool(record.get("deleted")),
    )
    event_status = record.get("event_status")

    audit = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "record_id": record_id,
        "company_id": company_id,
        "lifecycle": lifecycle,
        "event_status": event_status,
        "datetime": record.get("datetime"),
        "comment": (record.get("comment") or "")[:120],
    }

    if not is_yclients_gcal_mirror_enabled():
        audit["mirror"] = "disabled"
        _append_webhook_audit(audit)
        return {
            "status": "accepted",
            "company_id": company_id,
            "record_id": record_id,
            "lifecycle": lifecycle,
            "event_status": event_status,
            "calendar_event_id": None,
            "mirror": "disabled",
        }

    # Skip synthetic self-tests without real datetime
    if record_id in {"1", "42", "99"} and not _parse_yclients_datetime(record.get("datetime")):
        audit["mirror"] = "skipped_selftest"
        _append_webhook_audit(audit)
        return {
            "status": "accepted",
            "company_id": company_id,
            "record_id": record_id,
            "lifecycle": lifecycle,
            "event_status": event_status,
            "calendar_event_id": None,
            "mirror": "skipped_selftest",
        }

    try:
        if lifecycle in ("cancelled", "deleted") or event_status == "delete":
            mirror = delete_calendar_event_for_record(record_id)
        else:
            mirror = upsert_calendar_event(record)
    except Exception as exc:
        logger.exception(
            "yclients_gcal_mirror_failed record_id_tail=%s",
            record_id[-6:],
        )
        audit["mirror"] = "error"
        audit["error"] = type(exc).__name__
        _append_webhook_audit(audit)
        return {
            "status": "error",
            "company_id": company_id,
            "record_id": record_id,
            "lifecycle": lifecycle,
            "event_status": event_status,
            "calendar_event_id": None,
            "mirror": "error",
            "error": type(exc).__name__,
        }

    audit["mirror"] = mirror.get("action")
    audit["calendar_event_id"] = mirror.get("calendar_event_id")
    _append_webhook_audit(audit)
    logger.info(
        "yclients_sync_record record_id_tail=%s lifecycle=%s mirror=%s",
        record_id[-6:],
        lifecycle,
        mirror.get("action"),
    )
    return {
        "status": "accepted",
        "company_id": company_id,
        "record_id": record_id,
        "lifecycle": lifecycle,
        "event_status": event_status,
        "calendar_event_id": mirror.get("calendar_event_id"),
        "mirror": mirror.get("action"),
    }


def handle_webhook_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Process webhook body; idempotent upsert by company_id + record_id."""
    resource = str(payload.get("resource") or "").strip().lower()
    if resource and resource not in ("record",) and not isinstance(
        payload.get("resource"), dict
    ):
        return {
            "status": "ignored",
            "resource": resource,
            "reason": "not_record",
        }

    normalized = normalize_webhook_record(payload)
    if normalized["resource"] not in ("record", ""):
        return {
            "status": "ignored",
            "resource": normalized["resource"],
            "reason": "not_record",
        }
    return sync_record_to_calendar(normalized)


def extract_client_pii(record: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """PII fields available via Clients API / record.client (never expose publicly)."""
    client = record.get("client") or {}
    if not isinstance(client, dict):
        client = {}
    return {
        "name": client.get("name") or record.get("name"),
        "surname": client.get("surname") or record.get("surname"),
        "patronymic": client.get("patronymic") or record.get("patronymic"),
        "phone": client.get("phone") or record.get("phone"),
        "email": client.get("email") or record.get("email"),
    }
