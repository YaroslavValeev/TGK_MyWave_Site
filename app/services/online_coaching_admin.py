"""
Admin read helpers for MyWave Online Coaching.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from app.services.online_coaching_schema import ONLINE_REQUESTS_SHEET, REQUEST_STATUSES
from app.services.online_coaching_store import resolve_sheet_name, resolve_spreadsheet_id

SheetRecordsFn = Callable[[str, str], Sequence[Mapping[str, Any]]]

_ADMIN_HIDDEN_FIELDS = frozenset({"ip_hash", "injuries_or_limits"})


def sanitize_request_for_admin(record: Mapping[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for key, raw in record.items():
        if key in _ADMIN_HIDDEN_FIELDS:
            continue
        out[str(key)] = str(raw or "").strip()
    injuries = str(record.get("injuries_or_limits") or "").strip()
    out["has_injuries_info"] = "yes" if injuries else "no"
    return out


def _records_reader(sheet_records: Optional[SheetRecordsFn] = None) -> SheetRecordsFn:
    if sheet_records is not None:
        return sheet_records

    from app.services.google_sheets_service import read_records

    def reader(spreadsheet_id: str, sheet_name: str) -> Sequence[Mapping[str, Any]]:
        return read_records(spreadsheet_id, sheet_name)

    return reader


def list_online_requests(
    *,
    status_filter: Optional[str] = None,
    service_filter: Optional[str] = None,
    sheet_records: Optional[SheetRecordsFn] = None,
) -> List[Dict[str, str]]:
    spreadsheet_id = resolve_spreadsheet_id()
    if not spreadsheet_id:
        raise RuntimeError("SPREADSHEET_ID is empty")

    sheet_name = resolve_sheet_name("ONLINE_REQUESTS_SHEET_NAME", ONLINE_REQUESTS_SHEET)
    reader = _records_reader(sheet_records)
    records = reader(spreadsheet_id, sheet_name)

    status_needle = (status_filter or "").strip().lower()
    if status_needle and status_needle not in ("all", "*"):
        if status_needle not in REQUEST_STATUSES:
            raise ValueError(f"invalid_status_filter:{status_needle}")

    service_needle = (service_filter or "").strip().lower()

    rows: List[Dict[str, str]] = []
    for record in records:
        sanitized = sanitize_request_for_admin(record)
        if not sanitized.get("online_request_id"):
            continue
        status = sanitized.get("request_status", "").lower()
        if status_needle and status_needle not in ("all", "*") and status != status_needle:
            continue
        service = sanitized.get("service_type", "").lower()
        if service_needle and service_needle not in ("all", "*") and service != service_needle:
            continue
        rows.append(sanitized)

    rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return rows


def get_online_request(
    online_request_id: str,
    *,
    sheet_records: Optional[SheetRecordsFn] = None,
) -> Optional[Dict[str, str]]:
    req_id = (online_request_id or "").strip()
    if not req_id:
        return None
    for row in list_online_requests(sheet_records=sheet_records):
        if row.get("online_request_id", "").lower() == req_id.lower():
            return row
    return None


def get_online_request_detail(
    online_request_id: str,
    *,
    sheet_records: Optional[SheetRecordsFn] = None,
) -> Optional[Dict[str, str]]:
    """Full record for admin detail (includes injuries_or_limits)."""
    from app.services.online_coaching_store import find_request_by_id

    _row_number, record = find_request_by_id(online_request_id, sheet_records=sheet_records)
    if record is None:
        return None
    out = {str(k): str(v or "").strip() for k, v in record.items()}
    injuries = str(record.get("injuries_or_limits") or "").strip()
    out["has_injuries_info"] = "yes" if injuries else "no"
    return out
