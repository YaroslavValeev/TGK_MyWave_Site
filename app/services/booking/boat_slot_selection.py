"""Boat multi-slot selection helpers (PR53.1)."""
from __future__ import annotations

from typing import List, Tuple, Union

from app.config.booking_durations import BOAT_SET_MINUTES


def _time_to_minutes(time_str: str) -> int:
    parts = (time_str or "").strip().split(":")
    hours = int(parts[0]) if parts and parts[0].isdigit() else 0
    minutes = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    return hours * 60 + minutes


def _minutes_to_time(total: int) -> str:
    return f"{total // 60:02d}:{total % 60:02d}"


def are_consecutive_boat_slots(times: List[str]) -> bool:
    if len(times) <= 1:
        return True
    mins = sorted(_time_to_minutes(t) for t in times)
    for idx in range(1, len(mins)):
        if mins[idx] - mins[idx - 1] != BOAT_SET_MINUTES:
            return False
    return True


def normalize_boat_slot_booking(
    slot_times: List[str],
) -> Union[Tuple[str, int], List[str]]:
    """
    Map selected boat slot times to booking params.

    Consecutive selection → single range (start_time, set_count).
    Non-consecutive → list of individual slot times (each set_count=1).
    """
    cleaned = sorted({(t or "").strip() for t in slot_times if (t or "").strip()})
    if not cleaned:
        raise ValueError("empty_slot_times")
    if len(cleaned) == 1:
        return cleaned[0], 1
    if are_consecutive_boat_slots(cleaned):
        return cleaned[0], len(cleaned)
    return cleaned
