"""Web booking orchestration (gym=Calendar; boat=YCLIENTS when enabled)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from app.config.booking_features import is_phase2_availability_enabled
from app.config.booking_schedule import boat_provider
from app.config.yclients_config import (
    is_yclients_read_enabled,
    is_yclients_write_enabled,
)
from app.services.booking.availability import (
    SlotUnavailableError,
    assert_booking_available,
)
from app.services.booking.schedule_policy import assert_gym_slot_allowed
from app.services.booking.calendar_writer import (
    create_calendar_event,
    delete_calendar_event_best_effort,
)
from app.services.booking.client_resolver import resolve_client
from app.services.booking.constants import INTERNAL_STATUS_BOOKED
from app.services.booking.idempotency import (
    generate_booking_id,
    is_duplicate_web_booking,
)
from app.services.booking.phone import normalize_phone
from app.services.booking.sheets_writer import (
    compensate_workout_row,
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


class SheetsBookingError(BookingPipelineError):
    """Sheets journal incomplete after Calendar insert — compensated best-effort."""


@dataclass
class BookingResult:
    workout_id: str
    client_id: str
    booking_id: str
    client_workout_id: str
    internal_status: str = INTERNAL_STATUS_BOOKED


def _boat_uses_yclients() -> bool:
    return boat_provider() == "yclients" and is_yclients_write_enabled()


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
    # YCLIENTS and Phase2 Calendar both support multi-set boat.
    if _boat_uses_yclients() or is_phase2_availability_enabled():
        return min(n, MAX_BOAT_SET_COUNT)
    return 1


def _execute_boat_yclients_booking(
    *,
    date: str,
    time_norm: str,
    name: str,
    normalized_phone: str,
    client_id: str,
    booking_id: str,
    set_count: int,
    telegram_user_id: Optional[str],
) -> BookingResult:
    """Boat SoT = YCLIENTS; GCal via webhook/cron mirror; Sheets = journal."""
    from app.services.booking.providers.yclients import get_yclients_provider

    if not is_yclients_read_enabled():
        raise CalendarBookingError("yclients_read_disabled")

    provider = get_yclients_provider()
    phone_digits = "".join(ch for ch in normalized_phone if ch.isdigit())
    try:
        result = provider.create_booking(
            date_str=date,
            time_str=time_norm,
            client_name=name,
            client_phone=phone_digits,
            set_count=set_count,
            source="site",
            internal_id=booking_id,
            use_online=False,
        )
    except Exception as exc:
        logger.error(
            "booking_yclients_create_failed",
            extra={"service_type": "boat", "error": type(exc).__name__},
        )
        raise CalendarBookingError(str(exc)) from exc

    record_id = str(result.external_id or "").strip()
    if not record_id:
        raise CalendarBookingError("yclients_missing_record_id")

    workout_id = f"yc-{record_id}"
    try:
        cw_id = _write_sheets_journal(
            event_id=workout_id,
            client_id=client_id,
            date=date,
            time_norm=time_norm,
            service_type="boat",
            set_count=set_count,
        )
    except SheetsBookingError:
        # SoT already created — do not fail the user booking; journal is best-effort.
        logger.error(
            "booking_yclients_sheets_journal_failed",
            extra={"record_id_tail": record_id[-8:], "telegram": bool(telegram_user_id)},
        )
        cw_id = ""

    logger.info(
        "booking_yclients_created",
        extra={
            "record_id_tail": record_id[-8:],
            "date": date,
            "time": time_norm,
            "set_count": set_count,
        },
    )
    return BookingResult(
        workout_id=workout_id,
        client_id=client_id,
        booking_id=booking_id,
        client_workout_id=cw_id,
    )


def _compensate_partial_sheets_failure(
    *,
    event_id: str,
    workouts_written: bool,
    exc: Exception,
) -> None:
    """Option B: mark Workouts cancelled + best-effort Calendar delete."""
    compensation: list[str] = []
    if workouts_written:
        if compensate_workout_row(event_id):
            compensation.append("workout_row_mark_cancelled")
        else:
            compensation.append("workout_row_mark_failed")
    if delete_calendar_event_best_effort(event_id):
        compensation.append("calendar_delete")
    else:
        compensation.append("calendar_delete_failed")

    logger.error(
        "booking_sheets_partial_failure",
        extra={
            "workout_id_tail": str(event_id)[-8:],
            "workouts_written": workouts_written,
            "client_workouts_written": False,
            "compensation": "+".join(compensation) or "none",
            "error": type(exc).__name__,
        },
    )


def _write_sheets_journal(
    *,
    event_id: str,
    client_id: str,
    date: str,
    time_norm: str,
    service_type: str,
    set_count: int,
) -> str:
    workouts_written = False
    try:
        write_workout_row(
            workout_id=event_id,
            date=date,
            time=time_norm,
            service_type=service_type,
            set_count=set_count,
        )
        workouts_written = True
        return write_client_workout_row(
            client_id=client_id,
            workout_id=event_id,
            date=date,
            time=time_norm,
            service_type=service_type,
        )
    except Exception as exc:
        _compensate_partial_sheets_failure(
            event_id=event_id,
            workouts_written=workouts_written,
            exc=exc,
        )
        raise SheetsBookingError("sheets journal incomplete") from exc


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
    Gym: Calendar SoT + Sheets journal.

    Boat when BOAT_PROVIDER=yclients + YCLIENTS_WRITE:
      YCLIENTS SoT → Sheets journal (yc-{record_id}) → GCal via mirror.
    Else boat: legacy Calendar path (Phase1/Phase2).
    """
    normalized_phone = normalize_phone(phone)
    svc = (service_type or "gym").strip().lower()
    time_norm = time.strip()[:5]
    sc = _normalize_set_count(svc, set_count)
    use_yclients_boat = svc == "boat" and _boat_uses_yclients()

    if is_duplicate_web_booking(
        normalized_phone, date, time_norm, svc, set_count=sc
    ):
        logger.info(
            "booking_duplicate_detected",
            extra={"service_type": svc, "date": date, "time": time_norm, "set_count": sc},
        )
        raise DuplicateBookingError("duplicate slot for phone")

    booking_id = generate_booking_id()

    if svc == "gym":
        assert_gym_slot_allowed(date, time_norm)

    # Calendar occupancy check only for legacy paths (not YCLIENTS boat SoT).
    if is_phase2_availability_enabled() and not use_yclients_boat:
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

    if use_yclients_boat:
        return _execute_boat_yclients_booking(
            date=date,
            time_norm=time_norm,
            name=name,
            normalized_phone=normalized_phone,
            client_id=client.client_id,
            booking_id=booking_id,
            set_count=sc,
            telegram_user_id=telegram_user_id,
        )

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

    cw_id = _write_sheets_journal(
        event_id=event_id,
        client_id=client.client_id,
        date=date,
        time_norm=time_norm,
        service_type=svc,
        set_count=sc,
    )

    return BookingResult(
        workout_id=event_id,
        client_id=client.client_id,
        booking_id=booking_id,
        client_workout_id=cw_id,
    )
