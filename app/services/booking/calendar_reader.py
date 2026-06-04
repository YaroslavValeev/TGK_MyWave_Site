"""Read Google Calendar events for Phase 2 availability."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import List, Optional
from zoneinfo import ZoneInfo

from flask import current_app

from app.config.booking_durations import TRAINER_TRAVEL_BUFFER_MINUTES
from app.config.booking_features import is_phase2_availability_enabled

logger = logging.getLogger(__name__)

_SUMMARY_GYM = re.compile(r"(\(Зал\)|—\s*Зал\s*—|—\s*Зал\s*—)", re.IGNORECASE)
_SUMMARY_BOAT = re.compile(r"(\(Катер\)|—\s*Катер\s*—|Катер)", re.IGNORECASE)


@dataclass(frozen=True)
class BusyInterval:
    start: datetime
    end: datetime
    service_type: str  # gym | boat | unknown


def get_timezone() -> ZoneInfo:
    name = current_app.config.get("TIMEZONE", "Europe/Moscow")
    return ZoneInfo(name)


def day_bounds(date_str: str, tz: Optional[ZoneInfo] = None) -> tuple[datetime, datetime]:
    tz = tz or get_timezone()
    day = date.fromisoformat(date_str)
    start = datetime.combine(day, time.min, tzinfo=tz)
    return start, start + timedelta(days=1)


def day_bounds_with_buffer(
    date_str: str,
    buffer_minutes: int = TRAINER_TRAVEL_BUFFER_MINUTES,
    tz: Optional[ZoneInfo] = None,
) -> tuple[datetime, datetime]:
    """Expand query window for travel-buffer recheck (±buffer around local day)."""
    time_min, time_max = day_bounds(date_str, tz)
    buffer = timedelta(minutes=buffer_minutes)
    return time_min - buffer, time_max + buffer


def parse_service_type(event: dict) -> str:
    props = (event.get("extendedProperties") or {}).get("private") or {}
    st = (props.get("service_type") or "").strip().lower()
    if st in ("gym", "boat"):
        return st

    summary = event.get("summary") or ""
    if _SUMMARY_GYM.search(summary):
        return "gym"
    if _SUMMARY_BOAT.search(summary):
        return "boat"

    start, end = _parse_datetimes(event)
    if start and end:
        minutes = int((end - start).total_seconds() // 60)
        if minutes == 90:
            return "gym"
        if minutes > 0 and minutes % 30 == 0:
            return "boat"

    return "unknown"


def _parse_datetimes(event: dict) -> tuple[Optional[datetime], Optional[datetime]]:
    start_raw = (event.get("start") or {}).get("dateTime")
    end_raw = (event.get("end") or {}).get("dateTime")
    if not start_raw or not end_raw:
        return None, None
    start = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
    end = datetime.fromisoformat(end_raw.replace("Z", "+00:00"))
    return start, end


def event_to_busy_interval(event: dict) -> Optional[BusyInterval]:
    if (event.get("status") or "").lower() == "cancelled":
        return None
    start, end = _parse_datetimes(event)
    if not start or not end or end <= start:
        return None
    return BusyInterval(
        start=start,
        end=end,
        service_type=parse_service_type(event),
    )


def list_busy_intervals_for_date(date_str: str) -> List[BusyInterval]:
    """Load confirmed Calendar events for a local date."""
    from app.services.google import get_google_services

    tz = get_timezone()
    if is_phase2_availability_enabled():
        time_min, time_max = day_bounds_with_buffer(
            date_str, TRAINER_TRAVEL_BUFFER_MINUTES, tz
        )
    else:
        time_min, time_max = day_bounds(date_str, tz)
    calendar_id = current_app.config.get("GOOGLE_CALENDAR_ID")
    if not calendar_id:
        raise ValueError("GOOGLE_CALENDAR_ID is not configured")

    _, _, calendar_svc = get_google_services()
    result = (
        calendar_svc.events()
        .list(
            calendarId=calendar_id,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute(num_retries=2)
    )

    intervals: List[BusyInterval] = []
    for item in result.get("items", []):
        iv = event_to_busy_interval(item)
        if iv:
            intervals.append(iv)

    logger.info(
        "calendar_day_events_loaded",
        extra={"date": date_str, "count": len(intervals)},
    )
    return intervals
