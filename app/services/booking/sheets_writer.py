"""Sheets journal after Calendar event (Workouts + Client_Workouts)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from app.services.booking.calendar_writer import (
    booking_duration_minutes,
    get_calendar_location,
)
from app.services.booking.constants import SHEETS_STATUS_CONFIRMED

logger = logging.getLogger(__name__)

WORKOUT_STATUS_CANCELLED = "cancelled"


def _column_letter(index: int) -> str:
    """0-based column index → A, B, … (Workouts has ≤10 cols)."""
    return chr(65 + index)


def compensate_workout_row(workout_id: str) -> bool:
    """
    Best-effort rollback: mark Workouts row cancelled after partial journal failure.
    Uses prod headers: workout_status, current_capacity (see PROD_SHEETS_HEADERS).
    """
    wid = (workout_id or "").strip()
    if not wid:
        return False
    try:
        from flask import current_app

        from app.modules.sheets_access import get_google_sheet
        from app.services.google_sheets_service import update_record

        sheet = get_google_sheet("Workouts")
        matches = sheet.find_rows(workout_id=wid)
        if not matches:
            logger.warning(
                "compensate_workout_row_not_found",
                extra={"workout_id_tail": wid[-8:]},
            )
            return False

        row_idx, _row = matches[0]
        headers = sheet.values[0]
        sid = current_app.config["SPREADSHEET_ID"]

        if "workout_status" in headers:
            col = _column_letter(headers.index("workout_status"))
            update_record(
                sid,
                "Workouts",
                f"{col}{row_idx}",
                [WORKOUT_STATUS_CANCELLED],
            )
        if "current_capacity" in headers:
            col = _column_letter(headers.index("current_capacity"))
            update_record(sid, "Workouts", f"{col}{row_idx}", ["0"])

        logger.info(
            "compensate_workout_row_ok",
            extra={"workout_id_tail": wid[-8:]},
        )
        return True
    except Exception as exc:
        logger.error(
            "compensate_workout_row_failed",
            extra={"workout_id_tail": wid[-8:], "error": type(exc).__name__},
        )
        return False


def mark_client_workouts_cancelled(workout_id: str) -> int:
    """Mark Client_Workouts rows for workout_id as отменено. Returns updated count."""
    wid = (workout_id or "").strip()
    if not wid:
        return 0
    updated = 0
    try:
        from flask import current_app

        from app.modules.sheets_access import get_google_sheet
        from app.services.google_sheets_service import update_record

        sheet = get_google_sheet("Client_Workouts")
        matches = sheet.find_rows(workout_id=wid)
        if not matches:
            return 0
        headers = sheet.values[0]
        if "status" not in headers:
            return 0
        sid = current_app.config["SPREADSHEET_ID"]
        col = _column_letter(headers.index("status"))
        for row_idx, _row in matches:
            update_record(sid, "Client_Workouts", f"{col}{row_idx}", ["отменено"])
            updated += 1
        logger.info(
            "client_workouts_cancelled",
            extra={"workout_id_tail": wid[-8:], "rows": updated},
        )
    except Exception as exc:
        logger.error(
            "client_workouts_cancel_failed",
            extra={"workout_id_tail": wid[-8:], "error": type(exc).__name__},
        )
    return updated


def mark_yclients_journal_cancelled(record_id: str) -> dict:
    """Cancel Sheets journal for yc-{record_id} (Workouts + Client_Workouts)."""
    rid = str(record_id or "").strip()
    wid = rid if rid.startswith("yc-") else f"yc-{rid}"
    return {
        "workout_id": wid,
        "workouts": compensate_workout_row(wid),
        "client_workouts": mark_client_workouts_cancelled(wid),
    }


def write_workout_row(
    *,
    workout_id: str,
    date: str,
    time: str,
    service_type: str,
    set_count: int = 1,
) -> None:
    duration = booking_duration_minutes(service_type, set_count)
    location = get_calendar_location(service_type)

    data = {
        "workout_id": workout_id,
        "date": date,
        "time": time,
        "duration": str(duration),
        "location": location,
        "workout_type": service_type,
        "max_capacity": "",
        "coach_name": "",
        "workout_status": "active",
        "current_capacity": "1",
    }
    from app.modules.sheets_access import append_dict_to_sheet

    append_dict_to_sheet("Workouts", data)
    logger.info(
        "booking_row_written",
        extra={"sheet": "Workouts", "workout_id_tail": str(workout_id)[-8:]},
    )


def write_client_workout_row(
    *,
    client_id: str,
    workout_id: str,
    date: str,
    time: str,
    service_type: str,
) -> str:
    client_workout_id = f"cw_{uuid.uuid4().hex[:12]}"
    created_at = datetime.utcnow().isoformat()

    data = {
        "id": client_workout_id,
        "client_id": client_id,
        "workout_id": workout_id,
        "date": date,
        "time": time,
        "performance": "",
        "feedback": "",
        "payment_type": "single",
        "status": SHEETS_STATUS_CONFIRMED,
        "created_at": created_at,
    }
    from app.modules.sheets_access import append_dict_to_sheet

    append_dict_to_sheet("Client_Workouts", data)
    logger.info(
        "booking_row_written",
        extra={
            "sheet": "Client_Workouts",
            "workout_id_tail": str(workout_id)[-8:],
            "client_id_tail": str(client_id)[-8:],
        },
    )
    return client_workout_id
