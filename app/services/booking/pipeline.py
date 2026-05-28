"""Calendar-first web booking orchestration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from app.services.booking.calendar_writer import create_calendar_event
from app.services.booking.client_resolver import resolve_client
from app.services.booking.constants import INTERNAL_STATUS_BOOKED
from app.services.booking.idempotency import (
    generate_booking_id,
    is_duplicate_web_booking,
)
from app.services.booking.phone import normalize_phone
from app.services.booking.sheets_writer import (
    write_client_workout_row,
    write_workout_row,
)

logger = logging.getLogger(__name__)


class BookingPipelineError(Exception):
    """Base booking pipeline error."""


class DuplicateBookingError(BookingPipelineError):
    """Duplicate web booking for same slot."""


class CalendarBookingError(BookingPipelineError):
    """Calendar insert failed — Sheets must not be written."""


@dataclass
class BookingResult:
    workout_id: str
    client_id: str
    booking_id: str
    client_workout_id: str
    internal_status: str = INTERNAL_STATUS_BOOKED


def execute_web_booking(
    *,
    date: str,
    time: str,
    name: str,
    phone: str,
    service_type: str = "gym",
    telegram_user_id: Optional[str] = None,
) -> BookingResult:
    """
    Phase 1 pipeline:
    1. idempotency
    2. client resolve
    3. Calendar insert → event.id
    4. Workouts + Client_Workouts
    """
    normalized_phone = normalize_phone(phone)
    svc = (service_type or "gym").strip().lower()
    time_norm = time.strip()[:5]

    if is_duplicate_web_booking(normalized_phone, date, time_norm, svc):
        logger.info(
            "booking_duplicate_detected",
            extra={"service_type": svc, "date": date, "time": time_norm},
        )
        raise DuplicateBookingError("duplicate slot for phone")

    booking_id = generate_booking_id()

    if telegram_user_id:
        from app.services.booking.client_resolver import resolve_client_telegram

        client = resolve_client_telegram(telegram_user_id, name, normalized_phone)
    else:
        client = resolve_client(normalized_phone, name)

    try:
        event_id = create_calendar_event(
            date=date,
            time=time_norm,
            name=name,
            phone=normalized_phone,
            service_type=svc,
            booking_id=booking_id,
            client_id=client.client_id,
            telegram_user_id=telegram_user_id,
        )
    except Exception as exc:
        logger.error(
            "booking_calendar_event_failed",
            extra={"service_type": svc, "error": type(exc).__name__},
        )
        raise CalendarBookingError(str(exc)) from exc

    write_workout_row(
        workout_id=event_id,
        date=date,
        time=time_norm,
        service_type=svc,
    )
    cw_id = write_client_workout_row(
        client_id=client.client_id,
        workout_id=event_id,
        date=date,
        time=time_norm,
        service_type=svc,
    )

    return BookingResult(
        workout_id=event_id,
        client_id=client.client_id,
        booking_id=booking_id,
        client_workout_id=cw_id,
    )
