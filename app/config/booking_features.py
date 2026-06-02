"""Phase 2 booking feature flags (default OFF — production behavior unchanged)."""

from __future__ import annotations

import os
from typing import Dict

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _env_flag(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in _TRUTHY


def is_phase2_availability_enabled() -> bool:
    return _env_flag("BOOKING_PHASE2_AVAILABILITY")


def is_phase2_travel_buffer_enabled() -> bool:
    """Travel buffer requires availability engine (Phase 2 PR2+)."""
    return is_phase2_availability_enabled() and _env_flag("BOOKING_PHASE2_TRAVEL_BUFFER")


def is_phase2_multi_set_boat_enabled() -> bool:
    return _env_flag("BOOKING_PHASE2_MULTI_SET_BOAT")


def is_phase2_summary_v2_enabled() -> bool:
    return _env_flag("BOOKING_PHASE2_SUMMARY_V2")


def is_phase2_gym_location_v2_enabled() -> bool:
    return _env_flag("BOOKING_PHASE2_GYM_LOCATION_V2")


def get_booking_phase2_flags() -> Dict[str, bool]:
    """Snapshot for logging/tests (no secrets)."""
    return {
        "BOOKING_PHASE2_AVAILABILITY": is_phase2_availability_enabled(),
        "BOOKING_PHASE2_TRAVEL_BUFFER": is_phase2_travel_buffer_enabled(),
        "BOOKING_PHASE2_MULTI_SET_BOAT": is_phase2_multi_set_boat_enabled(),
        "BOOKING_PHASE2_SUMMARY_V2": is_phase2_summary_v2_enabled(),
        "BOOKING_PHASE2_GYM_LOCATION_V2": is_phase2_gym_location_v2_enabled(),
    }
