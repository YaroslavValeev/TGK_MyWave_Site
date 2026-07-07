"""
MyWave Online Coaching — data layer (append/read/update Google Sheets).
"""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from flask import current_app

from app.modules.logger import get_logger
from app.services.online_coaching_schema import (
    COMMENT_MAX_LEN,
    GOAL_MAX_LEN,
    INJURIES_MAX_LEN,
    IN_REVIEW_REMINDER_HOURS,
    LEVELS,
    MEDIA_FILES_HEADERS,
    MEDIA_FILES_SHEET,
    ONLINE_DIARIES_HEADERS,
    ONLINE_DIARIES_SHEET,
    ONLINE_FOLLOWUPS_HEADERS,
    ONLINE_FOLLOWUPS_SHEET,
    ONLINE_REQUESTS_HEADERS,
    ONLINE_REQUESTS_SHEET,
    PAYMENT_REMINDER_HOURS,
    PAYMENT_STATUSES,
    PAYMENT_TIMING_BY_SERVICE,
    PREFERRED_CHANNELS,
    REQUEST_STATUSES,
    REVIEW_DEADLINE_HOURS,
    REVIEW_TASK_MAX_LEN,
    SERVICE_TYPES,
    SHEET_HEADER_CONTRACTS,
    SPOT_OR_LOCATION_MAX_LEN,
    TRAINING_COMMENT_MAX_LEN,
    TRAINING_DATE_MAX_LEN,
    VIDEO_REMINDER_HOURS,
    col_letter,
    normalize_video_urls,
    payment_timing_for_service,
    validate_sheet_headers,
    validate_video_urls,
)

logger = get_logger(__name__)

_REQUEST_ID_RE = re.compile(r"^oc_req_[0-9a-f]{12,32}$", re.IGNORECASE)
_PHONE_DIGITS_RE = re.compile(r"\D+")

SheetAppendFn = Callable[[str, str, List[str]], Any]
SheetUpdateFn = Callable[[str, str, str, List[str]], Any]
SheetRecordsFn = Callable[[str, str], Sequence[Mapping[str, Any]]]


@dataclass(slots=True)
class OnlineCoachingInput:
    name: str
    phone: str
    service_type: str
    preferred_channel: str
    consent_personal_data: bool
    consent_version: str
    email: str = ""
    telegram_username: str = ""
    whatsapp_phone: str = ""
    max_contact: str = ""
    discipline: str = ""
    level: str = ""
    goal: str = ""
    injuries_or_limits: str = ""
    video_url: str = ""
    comment: str = ""
    source: str = "web_online_coaching"
    utm_source: str = ""
    utm_medium: str = ""
    utm_campaign: str = ""
    ip_hash: str = ""


@dataclass(slots=True)
class OnlineCoachingWriteResult:
    online_request_id: str
    request_status: str
    payment_required_timing: str
    sheet_name: str
    client_id: str = ""
    row_values: List[str] = field(default_factory=list)


def generate_request_id() -> str:
    return f"oc_req_{uuid.uuid4().hex[:16]}"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _iso_offset_hours(hours: int, *, base: Optional[datetime] = None) -> str:
    dt = base or datetime.now(timezone.utc)
    return (dt + timedelta(hours=hours)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _truthy_consent(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _normalize_phone(phone: str) -> str:
    digits = _PHONE_DIGITS_RE.sub("", phone or "")
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    return digits


def resolve_initial_status(service_type: str, video_url: str = "") -> str:
    """Initial status after apply. Video check always waits for media step (PR83)."""
    if service_type == "progress_month":
        return "waiting_payment"
    if service_type == "video_check":
        return "waiting_video"
    return "new"


def validate_application_payload(data: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []

    for field_name in ("name", "phone", "service_type", "preferred_channel", "consent_version"):
        if not str(data.get(field_name) or "").strip():
            errors.append(f"required:{field_name}")

    if not _truthy_consent(data.get("consent_personal_data")):
        errors.append("consent_personal_data_required")

    service_type = str(data.get("service_type") or "").strip().lower()
    if service_type and service_type not in SERVICE_TYPES:
        errors.append("invalid:service_type")

    preferred = str(data.get("preferred_channel") or "").strip().lower()
    if preferred and preferred not in PREFERRED_CHANNELS:
        errors.append("invalid:preferred_channel")

    phone_digits = _normalize_phone(str(data.get("phone") or ""))
    if len(phone_digits) < 10:
        errors.append("invalid:phone")

    email = str(data.get("email") or "").strip()
    if email and "@" not in email:
        errors.append("invalid:email")

    if preferred == "telegram" and len(str(data.get("telegram_username") or "").strip()) < 2:
        errors.append("required:telegram_username")
    elif preferred == "email" and "@" not in email:
        errors.append("required:email")

    discipline = str(data.get("discipline") or "").strip().lower()
    if discipline and discipline not in {"wakesurf", "wakeboard", "both", "other"}:
        errors.append("invalid:discipline")

    level = str(data.get("level") or "").strip().lower()
    if level and level not in LEVELS:
        errors.append("invalid:level")

    if len(str(data.get("goal") or "")) > GOAL_MAX_LEN:
        errors.append("invalid:goal_length")
    if len(str(data.get("comment") or "")) > COMMENT_MAX_LEN:
        errors.append("invalid:comment_length")
    if len(str(data.get("injuries_or_limits") or "")) > INJURIES_MAX_LEN:
        errors.append("invalid:injuries_or_limits_length")

    return errors


def parse_application_input(data: Mapping[str, Any]) -> OnlineCoachingInput:
    errors = validate_application_payload(data)
    if errors:
        raise ValueError("; ".join(errors))
    return OnlineCoachingInput(
        name=str(data["name"]).strip(),
        phone=str(data["phone"]).strip(),
        service_type=str(data["service_type"]).strip().lower(),
        preferred_channel=str(data["preferred_channel"]).strip().lower(),
        consent_personal_data=True,
        consent_version=str(data["consent_version"]).strip(),
        email=str(data.get("email") or "").strip(),
        telegram_username=str(data.get("telegram_username") or data.get("telegram") or "").strip(),
        whatsapp_phone=str(data.get("whatsapp_phone") or data.get("whatsapp") or "").strip(),
        max_contact=str(data.get("max_contact") or data.get("max") or "").strip(),
        discipline=str(data.get("discipline") or "").strip().lower(),
        level=str(data.get("level") or "").strip().lower(),
        goal=str(data.get("goal") or "").strip(),
        injuries_or_limits=str(data.get("injuries_or_limits") or "").strip(),
        video_url=str(data.get("video_url") or "").strip(),
        comment=str(data.get("comment") or "").strip(),
        source=str(data.get("source") or "web_online_coaching").strip() or "web_online_coaching",
        utm_source=str(data.get("utm_source") or "").strip(),
        utm_medium=str(data.get("utm_medium") or "").strip(),
        utm_campaign=str(data.get("utm_campaign") or "").strip(),
        ip_hash=str(data.get("ip_hash") or "").strip(),
    )


def build_request_row(
    online_request_id: str,
    payload: OnlineCoachingInput,
    *,
    client_id: str = "",
    request_status: str = "new",
    payment_status: str = "pending",
    created_at: Optional[str] = None,
    updated_at: Optional[str] = None,
) -> Dict[str, str]:
    if request_status not in REQUEST_STATUSES:
        raise ValueError(f"invalid_status:{request_status}")
    if payment_status not in PAYMENT_STATUSES:
        raise ValueError(f"invalid_payment_status:{payment_status}")
    if not _REQUEST_ID_RE.match(online_request_id):
        raise ValueError("invalid_online_request_id")

    ts = created_at or _utc_now_iso()
    upd = updated_at or ts
    timing = payment_timing_for_service(payload.service_type)
    return {
        "online_request_id": online_request_id,
        "created_at": ts,
        "updated_at": upd,
        "client_id": client_id,
        "name": payload.name,
        "phone": payload.phone,
        "email": payload.email,
        "preferred_channel": payload.preferred_channel,
        "telegram_username": payload.telegram_username,
        "whatsapp_phone": payload.whatsapp_phone,
        "max_contact": payload.max_contact,
        "service_type": payload.service_type,
        "discipline": payload.discipline,
        "level": payload.level,
        "goal": payload.goal,
        "injuries_or_limits": payload.injuries_or_limits,
        "video_url": payload.video_url,
        "comment": payload.comment,
        "payment_required_timing": timing,
        "payment_status": payment_status,
        "tbank_payment_url": "",
        "request_status": request_status,
        "assigned_to": "",
        "trainer_comment": "",
        "deadline_at": "",
        "next_followup_at": "",
        "diary_url": "",
        "source": payload.source,
        "utm_source": payload.utm_source,
        "utm_medium": payload.utm_medium,
        "utm_campaign": payload.utm_campaign,
        "consent_personal_data": "TRUE" if payload.consent_personal_data else "FALSE",
        "consent_version": payload.consent_version,
        "ip_hash": payload.ip_hash,
        "review_task": "",
        "training_comment": "",
        "training_date": "",
        "spot_or_location": "",
        "in_review_at": "",
        "paid_at": "",
    }


def row_dict_to_values(row: Mapping[str, str], headers: Sequence[str] = ONLINE_REQUESTS_HEADERS) -> List[str]:
    return [str(row.get(h, "") or "") for h in headers]


def resolve_spreadsheet_id() -> str:
    return (
        (current_app.config.get("SPREADSHEET_ID") if current_app else None)
        or os.getenv("SPREADSHEET_ID")
        or ""
    ).strip()


def resolve_sheet_name(config_key: str, default: str) -> str:
    return (
        (current_app.config.get(config_key) if current_app else None)
        or os.getenv(config_key)
        or default
    ).strip()


def _records_reader(sheet_records: Optional[SheetRecordsFn] = None) -> SheetRecordsFn:
    if sheet_records is not None:
        return sheet_records

    from app.services.google_sheets_service import read_records

    def reader(spreadsheet_id: str, sheet_name: str) -> Sequence[Mapping[str, Any]]:
        return read_records(spreadsheet_id, sheet_name)

    return reader


def _find_record_row(
    records: Sequence[Mapping[str, Any]],
    *,
    id_field: str,
    id_value: str,
) -> Tuple[Optional[int], Optional[Dict[str, str]]]:
    needle = id_value.strip().lower()
    for idx, record in enumerate(records):
        raw = str(record.get(id_field) or "").strip()
        if raw.lower() == needle:
            return idx + 2, {str(k): str(v or "") for k, v in record.items()}
    return None, None


def find_request_by_id(
    online_request_id: str,
    *,
    sheet_records: Optional[SheetRecordsFn] = None,
) -> Tuple[Optional[int], Optional[Dict[str, str]]]:
    spreadsheet_id = resolve_spreadsheet_id()
    if not spreadsheet_id:
        raise RuntimeError("SPREADSHEET_ID is empty")
    sheet_name = resolve_sheet_name("ONLINE_REQUESTS_SHEET_NAME", ONLINE_REQUESTS_SHEET)
    reader = _records_reader(sheet_records)
    records = reader(spreadsheet_id, sheet_name)
    return _find_record_row(records, id_field="online_request_id", id_value=online_request_id)


def update_request_fields(
    online_request_id: str,
    fields: Mapping[str, str],
    *,
    sheet_records: Optional[SheetRecordsFn] = None,
    sheet_update: Optional[SheetUpdateFn] = None,
) -> Dict[str, str]:
    row_number, record = find_request_by_id(online_request_id, sheet_records=sheet_records)
    if row_number is None or record is None:
        raise ValueError("request_not_found")

    spreadsheet_id = resolve_spreadsheet_id()
    sheet_name = resolve_sheet_name("ONLINE_REQUESTS_SHEET_NAME", ONLINE_REQUESTS_SHEET)
    updater = sheet_update
    if updater is None:
        from app.services.google_sheets_service import update_record as updater

    updates = dict(fields)
    updates["updated_at"] = _utc_now_iso()

    for key, value in updates.items():
        if key not in ONLINE_REQUESTS_HEADERS:
            raise ValueError(f"unknown_field:{key}")
        col_idx = ONLINE_REQUESTS_HEADERS.index(key)
        cell = f"{col_letter(col_idx)}{row_number}"
        updater(spreadsheet_id, sheet_name, cell, [str(value)])

    merged = dict(record)
    merged.update({k: str(v) for k, v in updates.items()})
    logger.info(
        "online_coaching_request_updated",
        extra={
            "online_request_id": online_request_id,
            "fields": sorted(updates.keys()),
        },
    )
    return merged


def _append_media_file(
    *,
    client_id: str,
    online_request_id: str,
    video_url: str,
    sheet_append: Optional[SheetAppendFn] = None,
) -> str:
    media_id = f"media_{uuid.uuid4().hex[:12]}"
    row = {
        "media_id": media_id,
        "client_id": client_id,
        "online_request_id": online_request_id,
        "media_type": "video",
        "url": video_url,
        "source": "web_online_coaching",
        "status": "received",
        "created_at": _utc_now_iso(),
    }
    values = row_dict_to_values(row, MEDIA_FILES_HEADERS)
    spreadsheet_id = resolve_spreadsheet_id()
    sheet_name = resolve_sheet_name("MEDIA_FILES_SHEET_NAME", MEDIA_FILES_SHEET)
    if sheet_append is not None:
        sheet_append(spreadsheet_id, sheet_name, values)
    else:
        from app.services.google_sheets_service import append_record

        append_record(spreadsheet_id, sheet_name, values)
    return media_id


def list_media_for_request(
    online_request_id: str,
    *,
    sheet_records: Optional[SheetRecordsFn] = None,
) -> List[Dict[str, str]]:
    spreadsheet_id = resolve_spreadsheet_id()
    if not spreadsheet_id:
        raise RuntimeError("SPREADSHEET_ID is empty")
    sheet_name = resolve_sheet_name("MEDIA_FILES_SHEET_NAME", MEDIA_FILES_SHEET)
    reader = _records_reader(sheet_records)
    records = reader(spreadsheet_id, sheet_name)
    needle = online_request_id.strip().lower()
    rows: List[Dict[str, str]] = []
    for record in records:
        if str(record.get("online_request_id") or "").strip().lower() != needle:
            continue
        rows.append({str(k): str(v or "").strip() for k, v in record.items()})
    rows.sort(key=lambda r: r.get("created_at", ""))
    return rows


def validate_media_payload(data: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    urls = normalize_video_urls(data.get("video_urls"))
    errors.extend(validate_video_urls(urls))

    review_task = str(data.get("review_task") or "").strip()
    if not review_task:
        errors.append("required:review_task")
    elif len(review_task) > REVIEW_TASK_MAX_LEN:
        errors.append("invalid:review_task_length")

    training_comment = str(data.get("training_comment") or "").strip()
    if not training_comment:
        errors.append("required:training_comment")
    elif len(training_comment) > TRAINING_COMMENT_MAX_LEN:
        errors.append("invalid:training_comment_length")

    training_date = str(data.get("training_date") or "").strip()
    if training_date and len(training_date) > TRAINING_DATE_MAX_LEN:
        errors.append("invalid:training_date_length")

    spot = str(data.get("spot_or_location") or "").strip()
    if spot and len(spot) > SPOT_OR_LOCATION_MAX_LEN:
        errors.append("invalid:spot_or_location_length")

    return errors


def append_request_media(
    online_request_id: str,
    data: Mapping[str, Any],
    *,
    sheet_append: Optional[SheetAppendFn] = None,
    sheet_records: Optional[SheetRecordsFn] = None,
    sheet_update: Optional[SheetUpdateFn] = None,
) -> Dict[str, str]:
    """Attach 1–3 video URLs and client task to an existing request."""
    errors = validate_media_payload(data)
    if errors:
        raise ValueError("; ".join(errors))

    _row_number, record = find_request_by_id(online_request_id, sheet_records=sheet_records)
    if record is None:
        raise ValueError("request_not_found")

    service_type = str(record.get("service_type") or "").strip().lower()
    current_status = str(record.get("request_status") or "").strip().lower()
    if service_type == "video_check" and current_status not in {"waiting_video", "new"}:
        if current_status == "video_received":
            raise ValueError("media_already_received")
        raise ValueError(f"invalid_status_for_media:{current_status}")

    urls = normalize_video_urls(data.get("video_urls"))
    review_task = str(data.get("review_task") or "").strip()
    training_comment = str(data.get("training_comment") or "").strip()
    training_date = str(data.get("training_date") or "").strip()
    spot_or_location = str(data.get("spot_or_location") or "").strip()
    client_id = str(record.get("client_id") or "")

    now = datetime.now(timezone.utc)
    deadline_at = _iso_offset_hours(REVIEW_DEADLINE_HOURS, base=now)
    next_followup_at = _iso_offset_hours(VIDEO_REMINDER_HOURS, base=now)

    update_fields: Dict[str, str] = {
        "video_url": urls[0],
        "review_task": review_task,
        "training_comment": training_comment,
        "training_date": training_date,
        "spot_or_location": spot_or_location,
        "request_status": "video_received",
        "deadline_at": deadline_at,
        "next_followup_at": next_followup_at,
    }
    merged = update_request_fields(
        online_request_id,
        update_fields,
        sheet_records=sheet_records,
        sheet_update=sheet_update,
    )

    for url in urls:
        _append_media_file(
            client_id=client_id,
            online_request_id=online_request_id,
            video_url=url,
            sheet_append=sheet_append,
        )

    merged["video_urls"] = urls
    logger.info(
        "online_coaching_media_appended",
        extra={
            "online_request_id": online_request_id,
            "video_count": len(urls),
            "request_status": "video_received",
        },
    )
    return merged


def build_status_transition_fields(new_status: str) -> Dict[str, str]:
    """Extra request fields when admin changes workflow status."""
    fields: Dict[str, str] = {"request_status": new_status}
    if new_status == "in_review":
        fields["in_review_at"] = _utc_now_iso()
        fields["next_followup_at"] = _iso_offset_hours(IN_REVIEW_REMINDER_HOURS)
    elif new_status == "waiting_payment":
        fields["next_followup_at"] = _iso_offset_hours(PAYMENT_REMINDER_HOURS)
    elif new_status == "paid":
        fields["paid_at"] = _utc_now_iso()
    elif new_status == "waiting_video":
        fields["next_followup_at"] = _iso_offset_hours(VIDEO_REMINDER_HOURS)
    return fields


def _log_bot_event_optional(client_id: str, event_type: str, metadata: str) -> None:
    try:
        from app.services.sheets_writer import save_bot_event_to_sheets

        save_bot_event_to_sheets(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            client_id=client_id,
            event_type=event_type,
            timestamp=_utc_now_iso(),
            metadata=metadata[:500],
            bot_response="",
        )
    except Exception as exc:
        logger.debug("online_coaching_bot_event_skipped error=%s", str(exc)[:120])


def log_admin_action(
    online_request_id: str,
    *,
    actor: str,
    action: str,
    summary: str,
    client_id: str = "",
) -> None:
    """Audit trail via Bot_Events (no PII in metadata)."""
    meta = f"online_request_id={online_request_id};action={action};summary={summary[:200]};actor={actor[:64]}"
    logger.info(
        "online_coaching_admin_action",
        extra={"online_request_id": online_request_id, "action": action, "actor": actor},
    )
    _log_bot_event_optional(client_id or "admin", f"online_coaching_{action}", meta)


def append_online_request(
    data: Mapping[str, Any],
    *,
    online_request_id: Optional[str] = None,
    sheet_append: Optional[SheetAppendFn] = None,
    sheet_records: Optional[SheetRecordsFn] = None,
    link_client: bool = True,
    log_bot_event: bool = True,
) -> OnlineCoachingWriteResult:
    payload = parse_application_input(data)
    req_id = online_request_id or generate_request_id()
    request_status = resolve_initial_status(payload.service_type, payload.video_url)
    payment_status = "pending"

    client_id = ""
    if link_client:
        from app.services.booking.client_resolver import resolve_client

        resolved = resolve_client(payload.phone, payload.name)
        client_id = resolved.client_id

    row_dict = build_request_row(
        req_id,
        payload,
        client_id=client_id,
        request_status=request_status,
        payment_status=payment_status,
    )
    if request_status == "waiting_video":
        row_dict["next_followup_at"] = _iso_offset_hours(VIDEO_REMINDER_HOURS)
    values = row_dict_to_values(row_dict)

    spreadsheet_id = resolve_spreadsheet_id()
    if not spreadsheet_id:
        raise RuntimeError("SPREADSHEET_ID is empty")

    sheet_name = resolve_sheet_name("ONLINE_REQUESTS_SHEET_NAME", ONLINE_REQUESTS_SHEET)
    if sheet_append is not None:
        sheet_append(spreadsheet_id, sheet_name, values)
    else:
        from app.services.google_sheets_service import append_record

        append_record(spreadsheet_id, sheet_name, values)

    # Media for video_check is submitted via POST .../media (PR83), not on apply.

    if log_bot_event and client_id:
        _log_bot_event_optional(
            client_id,
            "online_coaching_request_created",
            f"request_id={req_id};service={payload.service_type};status={request_status}",
        )

    logger.info(
        "online_coaching_request_appended",
        extra={
            "online_request_id": req_id,
            "request_status": request_status,
            "service_type": payload.service_type,
            "spreadsheet_id_tail": spreadsheet_id[-8:] if spreadsheet_id else None,
        },
    )
    return OnlineCoachingWriteResult(
        online_request_id=req_id,
        request_status=request_status,
        payment_required_timing=row_dict["payment_required_timing"],
        sheet_name=sheet_name,
        client_id=client_id,
        row_values=values,
    )


def append_diary_entry(
    online_request_id: str,
    entry: Mapping[str, Any],
    *,
    sheet_append: Optional[SheetAppendFn] = None,
    sheet_records: Optional[SheetRecordsFn] = None,
    sheet_update: Optional[SheetUpdateFn] = None,
) -> str:
    _row_number, record = find_request_by_id(online_request_id, sheet_records=sheet_records)
    if record is None:
        raise ValueError("request_not_found")

    diary_id = f"oc_diary_{uuid.uuid4().hex[:12]}"
    ts = _utc_now_iso()
    row = {
        "diary_id": diary_id,
        "client_id": record.get("client_id", ""),
        "online_request_id": online_request_id,
        "date": str(entry.get("date") or ts[:10]),
        "current_goal": str(entry.get("current_goal") or ""),
        "main_mistake": str(entry.get("main_mistake") or ""),
        "water_task": str(entry.get("water_task") or ""),
        "land_task": str(entry.get("land_task") or ""),
        "ofp_task": str(entry.get("ofp_task") or ""),
        "related_discipline_task": str(entry.get("related_discipline_task") or ""),
        "next_video_request": str(entry.get("next_video_request") or ""),
        "trainer_notes": str(entry.get("trainer_notes") or ""),
        "status": str(entry.get("status") or "active"),
        "created_at": ts,
        "updated_at": ts,
    }
    values = row_dict_to_values(row, ONLINE_DIARIES_HEADERS)
    spreadsheet_id = resolve_spreadsheet_id()
    sheet_name = resolve_sheet_name("ONLINE_DIARIES_SHEET_NAME", ONLINE_DIARIES_SHEET)
    if sheet_append is not None:
        sheet_append(spreadsheet_id, sheet_name, values)
    else:
        from app.services.google_sheets_service import append_record

        append_record(spreadsheet_id, sheet_name, values)

    diary_url = str(entry.get("diary_url") or "").strip()
    update_fields: Dict[str, str] = {"request_status": "diary_updated"}
    if diary_url:
        update_fields["diary_url"] = diary_url
    update_request_fields(
        online_request_id,
        update_fields,
        sheet_records=sheet_records,
        sheet_update=sheet_update,
    )
    return diary_id


def append_followup(
    online_request_id: str,
    entry: Mapping[str, Any],
    *,
    sheet_append: Optional[SheetAppendFn] = None,
    sheet_records: Optional[SheetRecordsFn] = None,
    sheet_update: Optional[SheetUpdateFn] = None,
) -> str:
    _row_number, record = find_request_by_id(online_request_id, sheet_records=sheet_records)
    if record is None:
        raise ValueError("request_not_found")

    followup_id = f"oc_fu_{uuid.uuid4().hex[:12]}"
    ts = _utc_now_iso()
    row = {
        "followup_id": followup_id,
        "online_request_id": online_request_id,
        "scheduled_at": str(entry.get("scheduled_at") or ""),
        "channel": str(entry.get("channel") or record.get("preferred_channel") or ""),
        "note": str(entry.get("note") or "")[:500],
        "status": str(entry.get("status") or "scheduled"),
        "created_at": ts,
    }
    values = row_dict_to_values(row, ONLINE_FOLLOWUPS_HEADERS)
    spreadsheet_id = resolve_spreadsheet_id()
    sheet_name = resolve_sheet_name("ONLINE_FOLLOWUPS_SHEET_NAME", ONLINE_FOLLOWUPS_SHEET)
    if sheet_append is not None:
        sheet_append(spreadsheet_id, sheet_name, values)
    else:
        from app.services.google_sheets_service import append_record

        append_record(spreadsheet_id, sheet_name, values)

    update_fields: Dict[str, str] = {"request_status": "followup_scheduled"}
    scheduled_at = str(entry.get("scheduled_at") or "").strip()
    if scheduled_at:
        update_fields["next_followup_at"] = scheduled_at
    update_request_fields(
        online_request_id,
        update_fields,
        sheet_records=sheet_records,
        sheet_update=sheet_update,
    )
    return followup_id


def log_followup_event(
    online_request_id: str,
    entry: Mapping[str, Any],
    *,
    sheet_append: Optional[SheetAppendFn] = None,
) -> str:
    """Append follow-up row without mutating request_status (cron reminders)."""
    followup_id = f"oc_fu_{uuid.uuid4().hex[:12]}"
    ts = _utc_now_iso()
    row = {
        "followup_id": followup_id,
        "online_request_id": online_request_id,
        "scheduled_at": str(entry.get("scheduled_at") or ""),
        "channel": str(entry.get("channel") or "telegram"),
        "note": str(entry.get("note") or "")[:500],
        "status": str(entry.get("status") or "logged"),
        "created_at": ts,
    }
    values = row_dict_to_values(row, ONLINE_FOLLOWUPS_HEADERS)
    spreadsheet_id = resolve_spreadsheet_id()
    sheet_name = resolve_sheet_name("ONLINE_FOLLOWUPS_SHEET_NAME", ONLINE_FOLLOWUPS_SHEET)
    if sheet_append is not None:
        sheet_append(spreadsheet_id, sheet_name, values)
    else:
        from app.services.google_sheets_service import append_record

        append_record(spreadsheet_id, sheet_name, values)
    return followup_id


def validate_all_online_coaching_sheet_contracts(
    *,
    spreadsheet_id: Optional[str] = None,
    header_reader: Optional[Callable[[str, str], Sequence[str]]] = None,
) -> Dict[str, Dict[str, Any]]:
    sid = spreadsheet_id or resolve_spreadsheet_id()
    report: Dict[str, Dict[str, Any]] = {}
    for sheet_name in SHEET_HEADER_CONTRACTS:
        if header_reader is not None:
            headers = list(header_reader(sid, sheet_name))
        else:
            from app.services.google import read_sheet

            _records, headers = read_sheet(sid, sheet_name)
        ok, missing = validate_sheet_headers(sheet_name, headers)
        report[sheet_name] = {"ok": ok, "missing_headers": missing}
    return report
