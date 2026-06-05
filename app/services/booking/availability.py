"""Phase 2 availability engine (Calendar SoT, behind feature flags)."""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from typing import Iterable, List, Optional
from zoneinfo import ZoneInfo

from app.config.booking_capacity import GYM_MAX_CLIENTS_PER_SLOT
from app.config.booking_grid import BOAT_GRID_END, BOAT_GRID_START
from app.config.booking_durations import (
    BOAT_SET_MINUTES,
    GYM_SLOT_MINUTES,
    TRAINER_TRAVEL_BUFFER_MINUTES,
)
from app.config.booking_features import (
    is_phase2_availability_enabled,
    is_phase2_multi_set_boat_enabled,
    is_phase2_travel_buffer_enabled,
)
from app.services.booking.calendar_reader import (
    BusyInterval,
    get_timezone,
    list_busy_intervals_for_date,
)

logger = logging.getLogger(__name__)


class SlotUnavailableError(Exception):
    """Candidate interval blocked (fresh Calendar read)."""


def intervals_overlap(
    a_start: datetime,
    a_end: datetime,
    b_start: datetime,
    b_end: datetime,
) -> bool:
    return a_start < b_end and b_start < a_end


def _slot_datetime(date_str: str, time_str: str, tz: ZoneInfo) -> datetime:
    hour, minute = map(int, time_str.strip()[:5].split(":"))
    return datetime.combine(date.fromisoformat(date_str), time(hour, minute), tzinfo=tz)


def filter_intervals_by_type(
    intervals: Iterable[BusyInterval], service_type: str
) -> List[BusyInterval]:
    return [iv for iv in intervals if iv.service_type == service_type]


def count_gym_occupancy(
    intervals: Iterable[BusyInterval],
    slot_start: datetime,
    slot_end: datetime,
) -> int:
    count = 0
    for iv in intervals:
        if iv.service_type != "gym":
            continue
        if intervals_overlap(slot_start, slot_end, iv.start, iv.end):
            count += 1
    return count


def boat_interval_blocked(
    intervals: Iterable[BusyInterval],
    candidate_start: datetime,
    candidate_end: datetime,
) -> bool:
    for iv in intervals:
        if iv.service_type != "boat":
            continue
        if intervals_overlap(candidate_start, candidate_end, iv.start, iv.end):
            return True
    return False


def travel_buffer_blocked(
    intervals: Iterable[BusyInterval],
    candidate_start: datetime,
    candidate_end: datetime,
    candidate_type: str,
    *,
    buffer_minutes: int = TRAINER_TRAVEL_BUFFER_MINUTES,
    enabled: Optional[bool] = None,
) -> bool:
    if candidate_type not in ("gym", "boat"):
        return False
    if enabled is None:
        enabled = is_phase2_travel_buffer_enabled()
    if not enabled:
        return False

    buffer = timedelta(minutes=buffer_minutes)
    other = "boat" if candidate_type == "gym" else "gym"

    for iv in intervals:
        if iv.service_type != other:
            continue
        if not (
            candidate_end + buffer <= iv.start or candidate_start >= iv.end + buffer
        ):
            logger.info(
                "availability_blocked_travel_buffer",
                extra={
                    "existing_type": other,
                    "candidate_type": candidate_type,
                    "gap_min": buffer_minutes,
                },
            )
            return True
    return False


def compute_max_set_count(
    date_str: str,
    start_time: str,
    intervals: Iterable[BusyInterval],
    tz: Optional[ZoneInfo] = None,
) -> int:
    """Max adjacent boat sets from start_time (inclusive)."""
    tz = tz or get_timezone()
    start = _slot_datetime(date_str, start_time, tz)
    grid_end = datetime.combine(date.fromisoformat(date_str), BOAT_GRID_END, tzinfo=tz)
    max_sets = 0
    n = 1
    while True:
        end = start + timedelta(minutes=BOAT_SET_MINUTES * n)
        if end > grid_end + timedelta(minutes=BOAT_SET_MINUTES):
            break
        if boat_interval_blocked(intervals, start, end):
            break
        if travel_buffer_blocked(intervals, start, end, "boat"):
            break
        max_sets = n
        n += 1
    return max_sets


def is_boat_range_available(
    date_str: str,
    start_time: str,
    set_count: int,
    intervals: Iterable[BusyInterval],
    tz: Optional[ZoneInfo] = None,
) -> bool:
    if set_count < 1:
        return False
    tz = tz or get_timezone()
    start = _slot_datetime(date_str, start_time, tz)
    end = start + timedelta(minutes=BOAT_SET_MINUTES * set_count)
    if boat_interval_blocked(intervals, start, end):
        return False
    if travel_buffer_blocked(intervals, start, end, "boat"):
        return False
    return True


def is_gym_slot_available(
    date_str: str,
    start_time: str,
    intervals: Iterable[BusyInterval],
    *,
    max_capacity: int = GYM_MAX_CLIENTS_PER_SLOT,
    tz: Optional[ZoneInfo] = None,
) -> tuple[bool, int]:
    tz = tz or get_timezone()
    cap = min(max_capacity, GYM_MAX_CLIENTS_PER_SLOT)
    start = _slot_datetime(date_str, start_time, tz)
    end = start + timedelta(minutes=GYM_SLOT_MINUTES)
    occupancy = count_gym_occupancy(intervals, start, end)
    remaining = max(0, cap - occupancy)
    available = remaining > 0 and not travel_buffer_blocked(
        intervals, start, end, "gym"
    )
    return available, remaining


def build_boat_slots_from_calendar(date_str: str) -> List[dict]:
    intervals = list_busy_intervals_for_date(date_str)
    tz = get_timezone()
    now = datetime.now(tz)
    day = date.fromisoformat(date_str)
    cur = datetime.combine(day, BOAT_GRID_START, tzinfo=tz)
    end_grid = datetime.combine(day, BOAT_GRID_END, tzinfo=tz)

    slots: List[dict] = []
    while cur <= end_grid:
        slot_end = cur + timedelta(minutes=BOAT_SET_MINUTES)
        time_str = cur.strftime("%H:%M")

        blocked = (
            cur < now
            or boat_interval_blocked(intervals, cur, slot_end)
            or travel_buffer_blocked(intervals, cur, slot_end, "boat")
        )
        if not blocked:
            entry: dict = {"time": time_str, "available": True}
            if is_phase2_multi_set_boat_enabled():
                entry["max_set_count"] = compute_max_set_count(
                    date_str, time_str, intervals, tz
                )
            slots.append(entry)

        logger.debug(
            "availability_check",
            extra={
                "service_type": "boat",
                "date": date_str,
                "start": time_str,
                "duration_min": BOAT_SET_MINUTES,
                "set_count": 1,
                "available": not blocked,
            },
        )
        cur += timedelta(minutes=BOAT_SET_MINUTES)

    return slots


def build_gym_slots_from_calendar(
    date_str: str,
    slot_rows: List[dict],
) -> List[dict]:
    """slot_rows: [{time, max_capacity}, ...] already filtered by schedule day."""
    intervals = list_busy_intervals_for_date(date_str)
    slots: List[dict] = []

    for rec in slot_rows:
        time_str = rec["time"]
        schedule_cap = int(rec.get("max_capacity") or GYM_MAX_CLIENTS_PER_SLOT)
        available, remaining = is_gym_slot_available(
            date_str,
            time_str,
            intervals,
            max_capacity=schedule_cap,
        )
        slots.append(
            {
                "time": time_str,
                "available": available,
                "remaining": remaining,
                "max_capacity": min(schedule_cap, GYM_MAX_CLIENTS_PER_SLOT),
            }
        )

        logger.debug(
            "availability_check",
            extra={
                "service_type": "gym",
                "date": date_str,
                "start": time_str,
                "duration_min": GYM_SLOT_MINUTES,
                "set_count": 1,
                "available": available,
                "remaining": remaining,
            },
        )

    return sorted(slots, key=lambda x: x["time"])


def get_boat_slots_phase2(date_str: str) -> List[dict]:
    if not is_phase2_availability_enabled():
        raise RuntimeError("Phase 2 availability flag is OFF")
    return build_boat_slots_from_calendar(date_str)


def assert_booking_available(
    date: str,
    time: str,
    service_type: str,
    set_count: int = 1,
) -> None:
    """
    Fresh Calendar read before insert. Raises SlotUnavailableError if blocked.
    No-op when BOOKING_PHASE2_AVAILABILITY is OFF (caller should skip).
    """
    svc = (service_type or "gym").strip().lower()
    n = max(1, int(set_count or 1))
    intervals = list_busy_intervals_for_date(date)

    if svc == "boat":
        if not is_boat_range_available(date, time, n, intervals):
            logger.info(
                "booking_recheck_blocked",
                extra={
                    "service_type": "boat",
                    "date": date,
                    "start": time[:5],
                    "set_count": n,
                },
            )
            raise SlotUnavailableError("boat_slot_occupied")
        return

    if svc == "gym":
        available, remaining = is_gym_slot_available(date, time, intervals)
        if not available:
            logger.info(
                "booking_recheck_blocked",
                extra={
                    "service_type": "gym",
                    "date": date,
                    "start": time[:5],
                    "remaining": remaining,
                },
            )
            if remaining <= 0:
                raise SlotUnavailableError("gym_capacity_full")
            raise SlotUnavailableError("gym_slot_unavailable")
        return

    raise SlotUnavailableError(f"unsupported_service_type:{svc}")
