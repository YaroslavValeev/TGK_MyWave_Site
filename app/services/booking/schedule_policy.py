"""Server-side seasonal gym schedule policy (Mon/Thu 19:00 until cutoff date)."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from app.config.booking_capacity import GYM_MAX_CLIENTS_PER_SLOT
from app.config.booking_schedule import gym_capacity
from app.config.booking_schedule import (
    gym_seasonal_start_time,
    gym_seasonal_weekdays,
    is_seasonal_rules_enabled,
    normalize_time_hhmm,
    parse_booking_date,
    seasonal_rules_until,
)

GYM_SEASONAL_ERROR_CODE = "gym_seasonal_schedule_restricted"
GYM_SEASONAL_MESSAGE = (
    "До 1 октября занятия в зале доступны только по понедельникам и четвергам вечером."
)


class GymSeasonalRestrictionError(Exception):
    """Gym booking blocked by seasonal schedule policy."""

    code = GYM_SEASONAL_ERROR_CODE

    def __init__(self, message: str = GYM_SEASONAL_MESSAGE) -> None:
        self.message = message
        super().__init__(message)


def is_seasonal_rules_active(for_date: date | str) -> bool:
    if not is_seasonal_rules_enabled():
        return False
    d = parse_booking_date(for_date) if isinstance(for_date, str) else for_date
    return d <= seasonal_rules_until()


def is_gym_weekday_allowed(for_date: date | str) -> bool:
    d = parse_booking_date(for_date) if isinstance(for_date, str) else for_date
    return d.weekday() in gym_seasonal_weekdays()


def is_gym_slot_allowed(for_date: date | str, time_str: str) -> bool:
    if not is_seasonal_rules_active(for_date):
        return True
    if not is_gym_weekday_allowed(for_date):
        return False
    return normalize_time_hhmm(time_str) == normalize_time_hhmm(gym_seasonal_start_time())


def assert_gym_slot_allowed(for_date: str, time_str: str) -> None:
    if not is_gym_slot_allowed(for_date, time_str):
        raise GymSeasonalRestrictionError()


def apply_gym_seasonal_slot_rows(
    date_str: str,
    slot_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """When seasonal rules active, server schedule wins over Sheets Schedule."""
    if not is_seasonal_rules_active(date_str):
        return slot_rows
    if not is_gym_weekday_allowed(date_str):
        return []
    cap = min(gym_capacity(), GYM_MAX_CLIENTS_PER_SLOT)
    return [
        {
            "time": normalize_time_hhmm(gym_seasonal_start_time()),
            "max_capacity": cap,
        }
    ]


def filter_gym_slots(date_str: str, slots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not is_seasonal_rules_active(date_str):
        return slots
    allowed_time = normalize_time_hhmm(gym_seasonal_start_time())
    filtered = [
        slot
        for slot in slots
        if normalize_time_hhmm(slot.get("time", "")) == allowed_time
        and is_gym_weekday_allowed(date_str)
    ]
    if filtered:
        return filtered
    if is_gym_weekday_allowed(date_str):
        return [
            {
                "time": allowed_time,
                "available": True,
                "remaining": GYM_MAX_CLIENTS_PER_SLOT,
                "max_capacity": GYM_MAX_CLIENTS_PER_SLOT,
            }
        ]
    return []


def get_gym_available_slots(date_str: str, base_slots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Public helper: apply seasonal policy on top of base gym slot list."""
    return filter_gym_slots(date_str, base_slots)


def seasonal_restriction_payload() -> Dict[str, Any]:
    return {
        "success": False,
        "status": "error",
        "error": GYM_SEASONAL_ERROR_CODE,
        "message": GYM_SEASONAL_MESSAGE,
    }
