"""Booking contract constants (v1.0)."""

from app.config.booking_location_constants import BOAT_CALENDAR_LOCATION_V1

SHEETS_STATUS_CONFIRMED = "подтверждено"
INTERNAL_STATUS_BOOKED = "booked"

SERVICE_LOCATION_SUMMARY = {
    "gym": "Зал",
    "boat": "Катер",
    "camp": "Camp",
}

# Phase 1 boat Calendar location (re-export for service-layer callers)
BOAT_CALENDAR_LOCATION = BOAT_CALENDAR_LOCATION_V1
