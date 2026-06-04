"""Calendar-first web booking orchestration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from app.config.booking_features import is_phase2_availability_enabled
from app.services.booking.availability import (
    SlotUnavailableError,
    assert_booking_available,
)
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

MAX_BOAT_SET_COUNT = 10


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


def _normalize_set_count(service_type: str, set_count: Optional[int]) -> int:
    svc = (service_type or "gym").strip().lower()
    try:
        n = int(set_count or 1)
    except (TypeError, ValueError):
        n = 1
    if n < 1:
        n = 1
    if svc != "boat":
        return 1
    if not is_phase2_availability_enabled():
        return 1
    return min(n, MAX_BOAT_SET_COUNT)


def execute_web_booking(
    *,
    date: str,
    time: str,
    name: str,
    phone: str,
    service_type: str = "gym",
    telegram_user_id: Optional[str] = None,
    set_count: Optional[int] = None,
) -> BookingResult:
    """
    Phase 1 pipeline (flags OFF):
    1. idempotency (point-in-time)
    2. client resolve
    3. Calendar insert → event.id
    4. Workouts + Client_Workouts

    Phase 2 (BOOKING_PHASE2_AVAILABILITY=1):
    + fresh Calendar recheck before insert
    + range idempotency; multi-set boat duration when set_count>1
    """
    normalized_phone = normalize_phone(phone)
    svc = (service_type or "gym").strip().lower()
    time_norm = time.strip()[:5]
    sc = _normalize_set_count(svc, set_count)

    if is_duplicate_web_booking(
        normalized_phone, date, time_norm, svc, set_count=sc
    ):
        logger.info(
            "booking_duplicate_detected",
            extra={"service_type": svc, "date": date, "time": time_norm, "set_count": sc},
        )
        raise DuplicateBookingError("duplicate slot for phone")

    booking_id = generate_booking_id()

    if is_phase2_availability_enabled():
        try:
            assert_booking_available(date, time_norm, svc, set_count=sc)
        except SlotUnavailableError as exc:
            logger.info(
                "booking_slot_unavailable",
                extra={
                    "service_type": svc,
                    "date": date,
                    "time": time_norm,
                    "reason": type(exc).__name__,
                },
            )
            raise

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
            set_count=sc,
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
        set_count=sc,
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
