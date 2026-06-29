"""
Admin read helpers for Social manual assign UI (MVP).

List/detail views read from Google Sheets. Writes go through social_sessions service.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from app.services.social_schema import (
    APPLICATION_STATUSES,
    SOCIAL_APPLICATIONS_SHEET,
    SOCIAL_AUDIT_LOG_SHEET,
)
from app.services.social_store import resolve_social_sheet_name, resolve_social_spreadsheet_id

SheetRecordsFn = Callable[[str, str], Sequence[Mapping[str, Any]]]

_ADMIN_HIDDEN_FIELDS = frozenset(
    {
        "health_notes",
        "motivation_text",
        "ip_hash",
        "internal_notes",
    }
)


def sanitize_application_for_admin(record: Mapping[str, Any]) -> Dict[str, str]:
    """Admin list/detail — no health text, no motivation, no ip_hash."""
    out: Dict[str, str] = {}
    for key, raw in record.items():
        if key in _ADMIN_HIDDEN_FIELDS:
            continue
        out[str(key)] = str(raw or "").strip()
    health = str(record.get("health_notes") or "").strip()
    out["has_safety_info"] = "yes" if health else "no"
    return out


def _records_reader(
    sheet_records: Optional[SheetRecordsFn] = None,
) -> SheetRecordsFn:
    if sheet_records is not None:
        return sheet_records

    from app.services.google_sheets_service import read_records

    def reader(spreadsheet_id: str, sheet_name: str) -> Sequence[Mapping[str, Any]]:
        return read_records(spreadsheet_id, sheet_name)

    return reader


def list_social_applications(
    *,
    status_filter: Optional[str] = None,
    sheet_records: Optional[SheetRecordsFn] = None,
) -> List[Dict[str, str]]:
    spreadsheet_id = resolve_social_spreadsheet_id()
    if not spreadsheet_id:
        raise RuntimeError("SOCIAL_SPREADSHEET_ID/SPREADSHEET_ID is empty")

    sheet_name = resolve_social_sheet_name(
        "SOCIAL_APPLICATIONS_SHEET_NAME",
        SOCIAL_APPLICATIONS_SHEET,
    )
    reader = _records_reader(sheet_records)
    records = reader(spreadsheet_id, sheet_name)

    needle = (status_filter or "").strip().lower()
    if needle and needle not in ("all", "*"):
        if needle not in APPLICATION_STATUSES:
            raise ValueError(f"invalid_status_filter:{needle}")

    rows: List[Dict[str, str]] = []
    for record in records:
        sanitized = sanitize_application_for_admin(record)
        if not sanitized.get("application_id"):
            continue
        status = sanitized.get("status", "").lower()
        if needle and needle not in ("all", "*") and status != needle:
            continue
        rows.append(sanitized)

    rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return rows


def get_social_application(
    application_id: str,
    *,
    sheet_records: Optional[SheetRecordsFn] = None,
) -> Optional[Dict[str, str]]:
    app_id = (application_id or "").strip()
    if not app_id:
        return None
    for row in list_social_applications(sheet_records=sheet_records):
        if row.get("application_id", "").lower() == app_id.lower():
            return row
    return None


def list_audit_events_for_application(
    application_id: str,
    *,
    sheet_records: Optional[SheetRecordsFn] = None,
) -> List[Dict[str, str]]:
    spreadsheet_id = resolve_social_spreadsheet_id()
    if not spreadsheet_id:
        raise RuntimeError("SOCIAL_SPREADSHEET_ID/SPREADSHEET_ID is empty")

    sheet_name = resolve_social_sheet_name(
        "SOCIAL_AUDIT_LOG_SHEET_NAME",
        SOCIAL_AUDIT_LOG_SHEET,
    )
    reader = _records_reader(sheet_records)
    records = reader(spreadsheet_id, sheet_name)
    needle = application_id.strip().lower()
    events: List[Dict[str, str]] = []
    for record in records:
        if str(record.get("application_id") or "").strip().lower() != needle:
            continue
        events.append({str(k): str(v or "").strip() for k, v in record.items()})
    events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return events
