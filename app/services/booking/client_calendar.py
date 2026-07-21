"""Client-facing Google Calendar / ICS helpers (Release S3).

SoT trainer calendar summaries (calendar_writer) are unchanged.
These helpers feed public booking.js titles/LOCATION/duration.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from app.config.booking_durations import BOAT_SET_MINUTES, GYM_LOCATION_LABEL, GYM_SLOT_MINUTES
from app.config.booking_venues import BOAT_VENUE, GYM_VENUE
from app.config.venue import MYWAVE_VENUE

_SERVICE_TITLE = {
    "boat": "Катер MyWave",
    "gym": "Зал MyWave",
}


def normalize_client_name(name: Optional[str]) -> str:
    cleaned = " ".join(str(name or "").strip().split())
    return cleaned or "Клиент"


def client_calendar_summary(service_type: str, client_name: Optional[str] = None) -> str:
    """Human calendar title without technical boat/gym tokens."""
    key = str(service_type or "").strip().lower()
    label = _SERVICE_TITLE.get(key, "MyWave")
    return f"{label} — {normalize_client_name(client_name)}"


def client_calendar_duration_minutes(service_type: str, set_count: int = 1) -> int:
    key = str(service_type or "").strip().lower()
    if key == "gym":
        return int(GYM_SLOT_MINUTES)
    if key == "boat":
        try:
            n = int(set_count or 1)
        except (TypeError, ValueError):
            n = 1
        n = max(1, min(n, 8))
        return int(BOAT_SET_MINUTES) * n
    if key == "camp":
        return 120
    return 60


def client_venue_for_service(service_type: str) -> Dict[str, str]:
    """Canonical venue payload for client calendars (no hardcoded maps in JS)."""
    key = str(service_type or "").strip().lower()
    if key == "boat":
        return {
            "service_type": "boat",
            "service_label": _SERVICE_TITLE["boat"],
            "location": str(MYWAVE_VENUE.get("location_label") or BOAT_VENUE.get("location_label") or "Катер MyWave"),
            "map_url": str(BOAT_VENUE.get("yandex_maps_url") or MYWAVE_VENUE.get("yandex_maps_url") or ""),
            "phone": str(MYWAVE_VENUE.get("telephone") or ""),
        }
    if key == "gym":
        return {
            "service_type": "gym",
            "service_label": _SERVICE_TITLE["gym"],
            "location": str(GYM_LOCATION_LABEL or GYM_VENUE.get("location_label") or "Зал MyWave"),
            "map_url": str(GYM_VENUE.get("yandex_maps_url") or ""),
            "phone": str(MYWAVE_VENUE.get("telephone") or ""),
        }
    return {
        "service_type": key or "",
        "service_label": "MyWave",
        "location": str(MYWAVE_VENUE.get("location_label") or "MyWave"),
        "map_url": str(MYWAVE_VENUE.get("yandex_maps_url") or ""),
        "phone": str(MYWAVE_VENUE.get("telephone") or ""),
    }


def build_client_venues_payload() -> Dict[str, Dict[str, str]]:
    return {
        "boat": client_venue_for_service("boat"),
        "gym": client_venue_for_service("gym"),
    }


def google_calendar_template_url(
    *,
    service_type: str,
    client_name: str,
    date: str,
    time: str,
    set_count: int = 1,
    phone: str = "",
    tz_offset_hours: int = 3,
) -> str:
    """Build Google Calendar TEMPLATE URL (Europe/Moscow local wall-clock encoded as UTC Z).

    Booking slots are Moscow local times; encode start as if local+offset → UTC for GCal dates=.
    """
    from datetime import datetime, timedelta, timezone

    venue = client_venue_for_service(service_type)
    title = client_calendar_summary(service_type, client_name)
    location = venue.get("location") or ""
    dur = client_calendar_duration_minutes(service_type, set_count)
    local = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    tz = timezone(timedelta(hours=tz_offset_hours))
    start_local = local.replace(tzinfo=tz)
    end_local = start_local + timedelta(minutes=dur)
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)

    def _fmt(dt: datetime) -> str:
        return dt.strftime("%Y%m%dT%H%M%SZ")

    details_parts = [f"Услуга: {venue.get('service_label') or service_type}"]
    if phone:
        details_parts.append(f"Телефон: {phone}")
    if venue.get("map_url"):
        details_parts.append(f"Карта: {venue['map_url']}")
    from urllib.parse import quote

    q_text = quote(title)
    q_loc = quote(location)
    q_details = quote("\n".join(details_parts))
    dates = f"{_fmt(start_utc)}/{_fmt(end_utc)}"
    return (
        "https://calendar.google.com/calendar/render?action=TEMPLATE"
        f"&text={q_text}&dates={dates}&details={q_details}&location={q_loc}"
    )


def build_ics_event(
    *,
    service_type: str,
    client_name: str,
    date: str,
    time: str,
    set_count: int = 1,
    phone: str = "",
    uid: Optional[str] = None,
    tz_offset_hours: int = 3,
) -> str:
    """Minimal VEVENT ICS for client download (Moscow wall clock → UTC Z)."""
    from datetime import datetime, timedelta, timezone

    venue = client_venue_for_service(service_type)
    title = client_calendar_summary(service_type, client_name)
    location = venue.get("location") or ""
    dur = client_calendar_duration_minutes(service_type, set_count)
    local = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    tz = timezone(timedelta(hours=tz_offset_hours))
    start_local = local.replace(tzinfo=tz)
    end_local = start_local + timedelta(minutes=dur)
    now = datetime.now(timezone.utc)

    def _fmt(dt: datetime) -> str:
        return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    desc_lines = [
        f"Услуга: {venue.get('service_label') or service_type}",
        f"Телефон: {phone or '—'}",
    ]
    if venue.get("map_url"):
        desc_lines.append(f"Карта: {venue['map_url']}")
    description = "\\n".join(desc_lines)
    event_uid = uid or f"mywave-{date}-{time.replace(':', '')}@mywavewake.ru"
    return "\r\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//MyWave//EN",
            "CALSCALE:GREGORIAN",
            "BEGIN:VEVENT",
            f"UID:{event_uid}",
            f"DTSTAMP:{_fmt(now)}",
            f"DTSTART:{_fmt(start_local)}",
            f"DTEND:{_fmt(end_local)}",
            f"SUMMARY:{title}",
            f"LOCATION:{location}",
            f"DESCRIPTION:{description}",
            "END:VEVENT",
            "END:VCALENDAR",
        ]
    )
