"""
MyWave Social Mission — manual session assign (PR56).

Creates Social_Sessions rows and audit log entries only.
No automatic calendar/booking writes from public /social apply.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from app.modules.logger import get_logger
from app.services.social_schema import (
    ASSIGNABLE_APPLICATION_STATUSES,
    SESSION_STATUSES,
    SESSION_STATUS_TRANSITIONS,
    SOCIAL_APPLICATIONS_HEADERS,
    SOCIAL_APPLICATIONS_SHEET,
    SOCIAL_AUDIT_LOG_HEADERS,
    SOCIAL_AUDIT_LOG_SHEET,
    SOCIAL_SESSIONS_HEADERS,
    SOCIAL_SESSIONS_SHEET,
)
from app.services.social_store import (
    resolve_social_sheet_name,
    resolve_social_spreadsheet_id,
)

logger = get_logger(__name__)

_SESSION_ID_RE = re.compile(r"^soc_sess_[0-9a-f]{12,32}$", re.IGNORECASE)
_APPLICATION_ID_RE = re.compile(r"^soc_app_[0-9a-f]{12,32}$", re.IGNORECASE)
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")

SheetAppendFn = Callable[[str, str, List[str]], Any]
SheetUpdateFn = Callable[[str, str, str, List[str]], Any]
SheetRecordsFn = Callable[[str, str], Sequence[Mapping[str, Any]]]


@dataclass(slots=True)
class SocialSessionAssignInput:
    application_id: str
    session_date: str
    session_time: str
    assigned_by: str
    location: str = ""
    service_type: str = ""
    coach: str = ""
    notes: str = ""
    calendar_event_id: str = ""
    booking_id: str = ""
    source: str = "manual_assign"


@dataclass(slots=True)
class SocialSessionResult:
    session_id: str
    application_id: str
    status: str
    session_date: str
    session_time: str
    location: str
    sheet_name: str
    row_values: List[str] = field(default_factory=list)


@dataclass(slots=True)
class SocialSessionStatusResult:
    session_id: str
    application_id: str
    old_status: str
    new_status: str
    sheet_name: str


def generate_session_id() -> str:
    return f"soc_sess_{uuid.uuid4().hex[:16]}"


def generate_audit_event_id() -> str:
    return f"soc_audit_{uuid.uuid4().hex[:16]}"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_assign_payload(data: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    app_id = str(data.get("application_id") or "").strip()
    if not app_id:
        errors.append("required:application_id")
    elif not _APPLICATION_ID_RE.match(app_id):
        errors.append("invalid:application_id")

    session_date = str(data.get("session_date") or "").strip()
    if not session_date:
        errors.append("required:session_date")
    elif not _DATE_RE.match(session_date):
        errors.append("invalid:session_date")

    session_time = str(data.get("session_time") or "").strip()
    if not session_time:
        errors.append("required:session_time")
    elif not _TIME_RE.match(session_time):
        errors.append("invalid:session_time")

    assigned_by = str(data.get("assigned_by") or "").strip()
    if not assigned_by:
        errors.append("required:assigned_by")

    notes = str(data.get("notes") or "")
    if len(notes) > 500:
        errors.append("invalid:notes_length")

    return errors


def parse_assign_input(data: Mapping[str, Any]) -> SocialSessionAssignInput:
    errors = validate_assign_payload(data)
    if errors:
        raise ValueError("; ".join(errors))
    return SocialSessionAssignInput(
        application_id=str(data["application_id"]).strip(),
        session_date=str(data["session_date"]).strip(),
        session_time=str(data["session_time"]).strip(),
        assigned_by=str(data["assigned_by"]).strip(),
        location=str(data.get("location") or "").strip(),
        service_type=str(data.get("service_type") or "").strip(),
        coach=str(data.get("coach") or "").strip(),
        notes=str(data.get("notes") or "").strip()[:500],
        calendar_event_id=str(data.get("calendar_event_id") or "").strip(),
        booking_id=str(data.get("booking_id") or "").strip(),
        source=str(data.get("source") or "manual_assign").strip() or "manual_assign",
    )


def build_session_row(
    session_id: str,
    payload: SocialSessionAssignInput,
    *,
    status: str = "scheduled",
    created_at: Optional[str] = None,
    updated_at: Optional[str] = None,
) -> Dict[str, str]:
    if status not in SESSION_STATUSES:
        raise ValueError(f"invalid_session_status:{status}")
    if not _SESSION_ID_RE.match(session_id):
        raise ValueError("invalid_session_id")

    ts = created_at or _utc_now_iso()
    upd = updated_at or ts
    return {
        "session_id": session_id,
        "application_id": payload.application_id,
        "created_at": ts,
        "updated_at": upd,
        "status": status,
        "assigned_by": payload.assigned_by,
        "session_date": payload.session_date,
        "session_time": payload.session_time,
        "location": payload.location,
        "service_type": payload.service_type,
        "coach": payload.coach,
        "notes": payload.notes,
        "calendar_event_id": payload.calendar_event_id,
        "booking_id": payload.booking_id,
        "source": payload.source,
    }


def session_row_to_values(row: Mapping[str, str]) -> List[str]:
    return [str(row.get(h, "") or "") for h in SOCIAL_SESSIONS_HEADERS]


def build_audit_row(
    *,
    actor: str,
    action: str,
    application_id: str,
    payload_summary: str,
    event_id: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> Dict[str, str]:
    return {
        "event_id": event_id or generate_audit_event_id(),
        "timestamp": timestamp or _utc_now_iso(),
        "actor": actor[:128],
        "action": action[:64],
        "application_id": application_id,
        "payload_summary": payload_summary[:500],
    }


def audit_row_to_values(row: Mapping[str, str]) -> List[str]:
    return [str(row.get(h, "") or "") for h in SOCIAL_AUDIT_LOG_HEADERS]


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


def _application_status_col() -> str:
    idx = SOCIAL_APPLICATIONS_HEADERS.index("status")
    return chr(ord("A") + idx)


def _application_updated_at_col() -> str:
    idx = SOCIAL_APPLICATIONS_HEADERS.index("updated_at")
    return chr(ord("A") + idx)


def _session_status_col() -> str:
    idx = SOCIAL_SESSIONS_HEADERS.index("status")
    return chr(ord("A") + idx)


def _session_updated_at_col() -> str:
    idx = SOCIAL_SESSIONS_HEADERS.index("updated_at")
    return chr(ord("A") + idx)


def append_social_audit_log(
    actor: str,
    action: str,
    application_id: str,
    payload_summary: str,
    *,
    sheet_append: Optional[SheetAppendFn] = None,
) -> str:
    row = build_audit_row(
        actor=actor,
        action=action,
        application_id=application_id,
        payload_summary=payload_summary,
    )
    values = audit_row_to_values(row)
    sheet_name = resolve_social_sheet_name("SOCIAL_AUDIT_LOG_SHEET_NAME", SOCIAL_AUDIT_LOG_SHEET)
    spreadsheet_id = resolve_social_spreadsheet_id()
    if not spreadsheet_id:
        raise RuntimeError("SOCIAL_SPREADSHEET_ID/SPREADSHEET_ID is empty")

    if sheet_append is not None:
        sheet_append(spreadsheet_id, sheet_name, values)
    else:
        from app.services.google_sheets_service import append_record

        append_record(spreadsheet_id, sheet_name, values)

    logger.info(
        "social_audit_appended",
        extra={
            "event_id": row["event_id"],
            "action": action,
            "application_id": application_id,
        },
    )
    return row["event_id"]


def _update_application_status(
    spreadsheet_id: str,
    sheet_name: str,
    row_number: int,
    new_status: str,
    *,
    sheet_update: Optional[SheetUpdateFn] = None,
) -> None:
    updated_at = _utc_now_iso()
    status_col = _application_status_col()
    updated_col = _application_updated_at_col()
    updater = sheet_update
    if updater is None:
        from app.services.google_sheets_service import update_record as updater

    updater(spreadsheet_id, sheet_name, f"{updated_col}{row_number}", [updated_at])
    updater(spreadsheet_id, sheet_name, f"{status_col}{row_number}", [new_status])


def manual_assign_social_session(
    data: Mapping[str, Any],
    *,
    session_id: Optional[str] = None,
    sheet_append: Optional[SheetAppendFn] = None,
    sheet_update: Optional[SheetUpdateFn] = None,
    sheet_records: Optional[SheetRecordsFn] = None,
    audit_append: Optional[Callable[..., str]] = None,
) -> SocialSessionResult:
    """
    Link Social_Applications.application_id → Social_Sessions row (status=scheduled).
    Updates application status to scheduled when assignable.
    """
    payload = parse_assign_input(data)
    sess_id = session_id or generate_session_id()
    row_dict = build_session_row(sess_id, payload, status="scheduled")
    values = session_row_to_values(row_dict)

    spreadsheet_id = resolve_social_spreadsheet_id()
    if not spreadsheet_id:
        raise RuntimeError("SOCIAL_SPREADSHEET_ID/SPREADSHEET_ID is empty")

    apps_sheet = resolve_social_sheet_name(
        "SOCIAL_APPLICATIONS_SHEET_NAME",
        SOCIAL_APPLICATIONS_SHEET,
    )
    sessions_sheet = resolve_social_sheet_name(
        "SOCIAL_SESSIONS_SHEET_NAME",
        SOCIAL_SESSIONS_SHEET,
    )

    records_reader = sheet_records
    if records_reader is None:
        from app.services.google_sheets_service import read_records

        def records_reader(sid: str, name: str) -> Sequence[Mapping[str, Any]]:
            return read_records(sid, name)

    app_records = records_reader(spreadsheet_id, apps_sheet)
    app_row_number, app_record = _find_record_row(
        app_records,
        id_field="application_id",
        id_value=payload.application_id,
    )
    if app_row_number is None or app_record is None:
        raise ValueError("application_not_found")

    current_app_status = str(app_record.get("status") or "new").strip().lower()
    if current_app_status not in ASSIGNABLE_APPLICATION_STATUSES:
        raise ValueError(f"application_not_assignable:{current_app_status}")

    session_records = records_reader(spreadsheet_id, sessions_sheet)
    for record in session_records:
        existing_app = str(record.get("application_id") or "").strip().lower()
        existing_status = str(record.get("status") or "").strip().lower()
        if existing_app == payload.application_id.lower() and existing_status == "scheduled":
            raise ValueError("session_already_scheduled")

    if sheet_append is not None:
        sheet_append(spreadsheet_id, sessions_sheet, values)
    else:
        from app.services.google_sheets_service import append_record

        append_record(spreadsheet_id, sessions_sheet, values)

    _update_application_status(
        spreadsheet_id,
        apps_sheet,
        app_row_number,
        "scheduled",
        sheet_update=sheet_update,
    )

    audit_fn = audit_append or append_social_audit_log
    audit_fn(
        payload.assigned_by,
        "session_assigned",
        payload.application_id,
        (
            f"session_id={sess_id}; status=scheduled; "
            f"date={payload.session_date}; time={payload.session_time}; "
            f"location={payload.location or '—'}"
        ),
    )
    audit_fn(
        payload.assigned_by,
        "application_status_changed",
        payload.application_id,
        f"old={current_app_status}; new=scheduled",
    )

    logger.info(
        "social_session_assigned",
        extra={
            "session_id": sess_id,
            "application_id": payload.application_id,
            "status": "scheduled",
        },
    )
    return SocialSessionResult(
        session_id=sess_id,
        application_id=payload.application_id,
        status="scheduled",
        session_date=payload.session_date,
        session_time=payload.session_time,
        location=payload.location,
        sheet_name=sessions_sheet,
        row_values=values,
    )


def transition_social_session_status(
    session_id: str,
    new_status: str,
    *,
    actor: str,
    sheet_update: Optional[SheetUpdateFn] = None,
    sheet_records: Optional[SheetRecordsFn] = None,
    audit_append: Optional[Callable[..., str]] = None,
) -> SocialSessionStatusResult:
    """scheduled → completed|cancelled with audit log."""
    if not _SESSION_ID_RE.match(session_id):
        raise ValueError("invalid_session_id")
    target = str(new_status or "").strip().lower()
    if target not in SESSION_STATUSES:
        raise ValueError(f"invalid_session_status:{target}")

    spreadsheet_id = resolve_social_spreadsheet_id()
    if not spreadsheet_id:
        raise RuntimeError("SOCIAL_SPREADSHEET_ID/SPREADSHEET_ID is empty")

    sessions_sheet = resolve_social_sheet_name(
        "SOCIAL_SESSIONS_SHEET_NAME",
        SOCIAL_SESSIONS_SHEET,
    )

    records_reader = sheet_records
    if records_reader is None:
        from app.services.google_sheets_service import read_records

        def records_reader(sid: str, name: str) -> Sequence[Mapping[str, Any]]:
            return read_records(sid, name)

    session_records = records_reader(spreadsheet_id, sessions_sheet)
    row_number, record = _find_record_row(
        session_records,
        id_field="session_id",
        id_value=session_id,
    )
    if row_number is None or record is None:
        raise ValueError("session_not_found")

    old_status = str(record.get("status") or "").strip().lower()
    if old_status == target:
        raise ValueError(f"session_status_unchanged:{old_status}")

    allowed = SESSION_STATUS_TRANSITIONS.get(old_status, frozenset())
    if target not in allowed:
        raise ValueError(f"session_transition_forbidden:{old_status}->{target}")

    updated_at = _utc_now_iso()
    status_col = _session_status_col()
    updated_col = _session_updated_at_col()
    updater = sheet_update
    if updater is None:
        from app.services.google_sheets_service import update_record as updater

    updater(spreadsheet_id, sessions_sheet, f"{updated_col}{row_number}", [updated_at])
    updater(spreadsheet_id, sessions_sheet, f"{status_col}{row_number}", [target])

    application_id = str(record.get("application_id") or "").strip()
    audit_fn = audit_append or append_social_audit_log
    audit_fn(
        actor,
        "session_status_changed",
        application_id,
        f"session_id={session_id}; old={old_status}; new={target}",
    )

    logger.info(
        "social_session_status_changed",
        extra={
            "session_id": session_id,
            "application_id": application_id,
            "old_status": old_status,
            "new_status": target,
        },
    )
    return SocialSessionStatusResult(
        session_id=session_id,
        application_id=application_id,
        old_status=old_status,
        new_status=target,
        sheet_name=sessions_sheet,
    )
