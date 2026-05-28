"""Sheets journal after Calendar event (Workouts + Client_Workouts)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from app.config.booking_durations import BOOKING_DURATION_MINUTES
from app.services.booking.calendar_writer import get_calendar_location
from app.services.booking.constants import SHEETS_STATUS_CONFIRMED

logger = logging.getLogger(__name__)


def write_workout_row(
    *,
    workout_id: str,
    date: str,
    time: str,
    service_type: str,
) -> None:
    duration = BOOKING_DURATION_MINUTES.get(service_type, 60)
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
