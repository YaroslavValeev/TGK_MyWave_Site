"""Calendar-first booking pipeline (Phase 1, TGbotAdmin contract v1.0)."""

from app.services.booking.availability import SlotUnavailableError
from app.services.booking.pipeline import (
    BookingPipelineError,
    CalendarBookingError,
    DuplicateBookingError,
    execute_web_booking,
)

__all__ = [
    "execute_web_booking",
    "DuplicateBookingError",
    "BookingPipelineError",
    "CalendarBookingError",
    "SlotUnavailableError",
]
