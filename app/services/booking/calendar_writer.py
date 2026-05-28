"""Google Calendar event creation (Calendar-first)."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional

from flask import current_app

from app.config.booking_durations import (
    BOOKING_DURATION_MINUTES,
    GYM_LOCATION_LABEL,
)
from app.config.venue import MYWAVE_VENUE
from app.services.booking.constants import (
    SERVICE_LOCATION_SUMMARY,
    BOAT_CALENDAR_LOCATION,
)

logger = logging.getLogger(__name__)


def build_event_summary(
    service_type: str,
    name: str,
    *,
    telegram_user_id: Optional[str] = None,
    booking_id: Optional[str] = None,
) -> str:
    location_label = SERVICE_LOCATION_SUMMARY.get(service_type, service_type or "Зал")
    if telegram_user_id:
        marker = f"(ID: {telegram_user_id})"
    else:
        bid = booking_id or "unknown"
        marker = f"(WEB_ID: {bid})"
    return f"Тренировка ({location_label}) — {name} {marker}"


def build_event_description(
    *,
    phone: str,
    client_id: str,
    workout_id: str,
    service_type: str,
    booking_id: str,
    telegram_user_id: Optional[str] = None,
) -> str:
    lines = [
        f"phone: {phone}",
        f"telegram_id: {telegram_user_id or ''}",
        f"client_id: {client_id}",
        f"workout_id: {workout_id}",
        "source: web" if not telegram_user_id else "telegram",
        f"service_type: {service_type}",
        f"booking_id: {booking_id}",
    ]
    return "\n".join(lines)


def get_calendar_location(service_type: str) -> str:
    if service_type == "boat":
        return BOAT_CALENDAR_LOCATION
    if service_type == "gym":
        return GYM_LOCATION_LABEL
    return MYWAVE_VENUE.get("location_label", "")


def build_calendar_event_body(
    *,
    date: str,
    time: str,
    name: str,
    phone: str,
    service_type: str,
    booking_id: str,
    client_id: str,
    telegram_user_id: Optional[str] = None,
) -> dict:
    start = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    duration_min = BOOKING_DURATION_MINUTES.get(service_type, 60)
    end = start + timedelta(minutes=duration_min)
    tz = current_app.config.get("TIMEZONE", "Europe/Moscow")

    phone_hash = hashlib.sha256(phone.encode("utf-8")).hexdigest()[:16]

    return {
        "summary": build_event_summary(
            service_type,
            name,
            telegram_user_id=telegram_user_id,
            booking_id=booking_id,
        ),
        "description": build_event_description(
            phone=phone,
            client_id=client_id,
            workout_id="",  # filled after insert if needed; event.id known post-insert
            service_type=service_type,
            booking_id=booking_id,
            telegram_user_id=telegram_user_id,
        ),
        "location": get_calendar_location(service_type),
        "start": {"dateTime": start.isoformat(), "timeZone": tz},
        "end": {"dateTime": end.isoformat(), "timeZone": tz},
        "extendedProperties": {
            "private": {
                "booking_id": booking_id,
                "client_id": client_id,
                "source": "web" if not telegram_user_id else "telegram",
                "service_type": service_type,
                "phone_hash": phone_hash,
            }
        },
    }


def create_calendar_event(
    *,
    date: str,
    time: str,
    name: str,
    phone: str,
    service_type: str,
    booking_id: str,
    client_id: str,
    telegram_user_id: Optional[str] = None,
) -> str:
    """Insert Calendar event; return event.id (workout_id)."""
    from app.services.google import get_google_services

    body = build_calendar_event_body(
        date=date,
        time=time,
        name=name,
        phone=phone,
        service_type=service_type,
        booking_id=booking_id,
        client_id=client_id,
        telegram_user_id=telegram_user_id,
    )

    _, _, calendar_svc = get_google_services()
    calendar_id = current_app.config["GOOGLE_CALENDAR_ID"]
    result = (
        calendar_svc.events()
        .insert(calendarId=calendar_id, body=body)
        .execute(num_retries=2)
    )
    event_id = result.get("id")
    if not event_id:
        raise RuntimeError("Calendar insert returned no event.id")

    logger.info(
        "booking_calendar_event_created",
        extra={
            "workout_id_tail": str(event_id)[-8:],
            "service_type": service_type,
            "booking_id_tail": str(booking_id)[-8:],
        },
    )
    return event_id
