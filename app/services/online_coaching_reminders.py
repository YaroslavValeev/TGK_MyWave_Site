"""
MyWave Online Coaching — follow-up reminders (cron-driven).

Scans `next_followup_at` in Online_Requests and notifies trainer via Telegram.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from app.modules.logger import get_logger
from app.services.online_coaching_notifications import (
    notify_payment_needed,
    notify_video_received,
)
from app.services.online_coaching_schema import (
    IN_REVIEW_REMINDER_HOURS,
    ONLINE_REQUESTS_SHEET,
    PAYMENT_REMINDER_HOURS,
    VIDEO_REMINDER_HOURS,
)
from app.services.online_coaching_store import (
    log_followup_event,
    resolve_sheet_name,
    resolve_spreadsheet_id,
    update_request_fields,
)

logger = get_logger(__name__)

SheetRecordsFn = Callable[[str, str], Sequence[Mapping[str, Any]]]

REMINDER_STATUSES = frozenset({
    "waiting_video",
    "in_review",
    "waiting_payment",
})

TERMINAL_STATUSES = frozenset({"completed", "cancelled", "paid", "subscription_active"})


def _parse_iso(ts: str) -> Optional[datetime]:
    text = str(ts or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_offset_hours(hours: int, base: Optional[datetime] = None) -> str:
    base_dt = base or _utc_now()
    from datetime import timedelta

    return (base_dt + timedelta(hours=hours)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def list_due_reminder_requests(
    *,
    now: Optional[datetime] = None,
    sheet_records: Optional[SheetRecordsFn] = None,
) -> List[Dict[str, str]]:
    """Return requests where next_followup_at <= now and status is reminder-eligible."""
    spreadsheet_id = resolve_spreadsheet_id()
    if not spreadsheet_id:
        raise RuntimeError("SPREADSHEET_ID is empty")

    if sheet_records is None:
        from app.services.google_sheets_service import read_records

        def sheet_records(spreadsheet_id: str, sheet_name: str) -> Sequence[Mapping[str, Any]]:
            return read_records(spreadsheet_id, sheet_name)

    sheet_name = resolve_sheet_name("ONLINE_REQUESTS_SHEET_NAME", ONLINE_REQUESTS_SHEET)
    records = sheet_records(spreadsheet_id, sheet_name)
    now_dt = now or _utc_now()

    due: List[Dict[str, str]] = []
    for record in records:
        row = {str(k): str(v or "").strip() for k, v in record.items()}
        req_id = row.get("online_request_id", "")
        if not req_id:
            continue
        status = row.get("request_status", "").lower()
        if status in TERMINAL_STATUSES or status not in REMINDER_STATUSES:
            continue
        followup_at = _parse_iso(row.get("next_followup_at", ""))
        if followup_at is None or followup_at > now_dt:
            continue
        due.append(row)

    due.sort(key=lambda r: r.get("next_followup_at", ""))
    return due


def _reminder_hours_for_status(status: str) -> int:
    if status == "in_review":
        return IN_REVIEW_REMINDER_HOURS
    if status == "waiting_payment":
        return PAYMENT_REMINDER_HOURS
    return VIDEO_REMINDER_HOURS


def _reminder_note(status: str) -> str:
    if status == "waiting_video":
        return "Напоминание: клиент ещё не отправил видео"
    if status == "in_review":
        return "Напоминание: разбор в работе — проверьте дедлайн"
    if status == "waiting_payment":
        return "Напоминание: ожидается оплата"
    return f"Напоминание по статусу {status}"


def _notify_for_status(record: Mapping[str, Any]) -> bool:
    status = str(record.get("request_status") or "").lower()
    if status == "waiting_video":
        return notify_video_received(record)
    if status == "waiting_payment":
        return notify_payment_needed(record)
    if status == "in_review":
        from app.services.online_coaching_notifications import notify_review_ready

        return notify_review_ready(record)
    return False


def process_due_reminders(
    *,
    dry_run: bool = False,
    now: Optional[datetime] = None,
    sheet_records: Optional[SheetRecordsFn] = None,
    sheet_append=None,
    sheet_update=None,
) -> Dict[str, Any]:
    """Process all due reminders; reschedule next_followup_at."""
    due = list_due_reminder_requests(now=now, sheet_records=sheet_records)
    processed: List[str] = []
    skipped: List[str] = []

    for record in due:
        req_id = record.get("online_request_id", "")
        status = record.get("request_status", "").lower()
        if dry_run:
            processed.append(req_id)
            continue

        try:
            sent = _notify_for_status(record)
            hours = _reminder_hours_for_status(status)
            next_at = _iso_offset_hours(hours)
            update_request_fields(
                req_id,
                {"next_followup_at": next_at},
                sheet_records=sheet_records,
                sheet_update=sheet_update,
            )
            log_followup_event(
                req_id,
                {
                    "scheduled_at": next_at,
                    "channel": "telegram",
                    "note": _reminder_note(status),
                    "status": "sent" if sent else "skipped",
                },
                sheet_append=sheet_append,
            )
            processed.append(req_id)
            logger.info(
                "online_coaching_reminder_sent",
                extra={"online_request_id": req_id, "status": status, "sent": sent},
            )
        except Exception as exc:
            skipped.append(req_id)
            logger.warning(
                "online_coaching_reminder_failed",
                extra={"online_request_id": req_id, "error": str(exc)[:200]},
            )

    return {"due_count": len(due), "processed": processed, "skipped": skipped, "dry_run": dry_run}
