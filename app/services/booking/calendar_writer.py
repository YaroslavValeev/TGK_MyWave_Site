"""Google Calendar event creation (Calendar-first)."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional

from flask import current_app

from app.config.booking_durations import (
    BOAT_SET_MINUTES,
    BOOKING_DURATION_MINUTES,
    GYM_LOCATION_LABEL,
    GYM_SLOT_MINUTES,
)
from app.config.booking_schedule import is_operational_summary_enabled
from app.config.booking_features import (
    is_phase2_availability_enabled,
    is_phase2_gym_location_v2_enabled,
    is_phase2_summary_v2_enabled,
)
from app.config.booking_location_constants import (
    BOAT_CALENDAR_LOCATION,
    BOAT_CALENDAR_LOCATION_V1,
    GYM_CALENDAR_LOCATION,
)
from app.config.venue import MYWAVE_VENUE
from app.services.booking.client_display import build_client_display_name
from app.services.booking.constants import SERVICE_LOCATION_SUMMARY

logger = logging.getLogger(__name__)


def format_boat_sets_label(set_count: int) -> str:
    n = max(1, int(set_count))
    if n == 1:
        return "1 сет"
    if 2 <= n <= 4:
        return f"{n} сета"
    return f"{n} сетов"


def booking_duration_minutes(service_type: str, set_count: int = 1) -> int:
    svc = (service_type or "gym").strip().lower()
    if svc == "gym":
        return GYM_SLOT_MINUTES
    if svc == "boat":
        n = max(1, int(set_count or 1))
        if is_phase2_availability_enabled():
            return BOAT_SET_MINUTES * n
        return BOOKING_DURATION_MINUTES.get("boat", BOAT_SET_MINUTES)
    return BOOKING_DURATION_MINUTES.get(svc, 60)


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


def build_event_summary_operational(
    service_type: str,
    name: str,
    *,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
) -> str:
    display = build_client_display_name(
        {
            "name": name,
            "first_name": first_name,
            "last_name": last_name,
        }
    )
    svc = (service_type or "gym").strip().lower()
    if svc == "gym":
        return f"Зал MyWave — {display}"
    if svc == "boat":
        return f"Катер / Руза — {display}"
    location_label = SERVICE_LOCATION_SUMMARY.get(svc, svc)
    return f"{location_label} — {display}"


def build_event_summary_v2(
    service_type: str,
    name: str,
    *,
    set_count: int = 1,
    booking_id: Optional[str] = None,
) -> str:
    bid = booking_id or "unknown"
    marker = f"(WEB_ID: {bid})"
    svc = (service_type or "gym").strip().lower()
    if svc == "gym":
        return f"Тренировка — Зал — {name} {marker}"
    if svc == "boat":
        sets_part = format_boat_sets_label(set_count)
        return f"Тренировка — Катер — {sets_part} — {name} {marker}"
    location_label = SERVICE_LOCATION_SUMMARY.get(svc, svc)
    return f"Тренировка — {location_label} — {name} {marker}"


def resolve_event_summary(
    service_type: str,
    name: str,
    *,
    set_count: int = 1,
    telegram_user_id: Optional[str] = None,
    booking_id: Optional[str] = None,
) -> str:
    if telegram_user_id:
        return build_event_summary(
            service_type,
            name,
            telegram_user_id=telegram_user_id,
            booking_id=booking_id,
        )
    if is_operational_summary_enabled():
        return build_event_summary_operational(service_type, name)
    if is_phase2_summary_v2_enabled():
        return build_event_summary_v2(
            service_type,
            name,
            set_count=set_count,
            booking_id=booking_id,
        )
    return build_event_summary(
        service_type,
        name,
        booking_id=booking_id,
    )


def build_event_description(
    *,
    phone: str,
    client_id: str,
    workout_id: str,
    service_type: str,
    booking_id: str,
    name: str = "",
    telegram_user_id: Optional[str] = None,
    set_count: int = 1,
    duration_min: Optional[int] = None,
    start_iso: Optional[str] = None,
    end_iso: Optional[str] = None,
) -> str:
    display_name = build_client_display_name({"name": name})
    svc = (service_type or "gym").strip().lower()
    lines = [
        f"Услуга: {'Тренировка в зале' if svc == 'gym' else 'Тренировка на катере'}",
        f"Клиент: {display_name}",
        f"Телефон: {phone}",
        f"Источник: {'telegram' if telegram_user_id else 'site'}",
        "Статус: подтверждено",
        f"phone: {phone}",
        f"telegram_id: {telegram_user_id or ''}",
        f"client_id: {client_id}",
        f"workout_id: {workout_id}",
        f"service_type: {service_type}",
        f"booking_id: {booking_id}",
    ]
    if is_phase2_availability_enabled():
        dur = duration_min or booking_duration_minutes(service_type, set_count)
        lines.extend(
            [
                f"set_count: {max(1, int(set_count))}",
                f"duration_min: {dur}",
            ]
        )
        if start_iso:
            lines.append(f"start_time: {start_iso}")
        if end_iso:
            lines.append(f"end_time: {end_iso}")
    return "\n".join(lines)


def get_calendar_location(service_type: str) -> str:
    svc = (service_type or "").strip().lower()
    if is_phase2_gym_location_v2_enabled():
        if svc == "gym":
            return GYM_CALENDAR_LOCATION
        if svc == "boat":
            return BOAT_CALENDAR_LOCATION
    if svc == "boat":
        return BOAT_CALENDAR_LOCATION_V1
    if svc == "gym":
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
    set_count: int = 1,
) -> dict:
    start = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    duration_min = booking_duration_minutes(service_type, set_count)
    end = start + timedelta(minutes=duration_min)
    tz = current_app.config.get("TIMEZONE", "Europe/Moscow")

    phone_hash = hashlib.sha256(phone.encode("utf-8")).hexdigest()[:16]
    start_iso = start.isoformat()
    end_iso = end.isoformat()
    sc = max(1, int(set_count or 1))

    private_props = {
        "booking_id": booking_id,
        "client_id": client_id,
        "source": "web" if not telegram_user_id else "telegram",
        "service_type": service_type,
        "phone_hash": phone_hash,
        "booking_provider": "mywave",
        "location_code": "ruza" if (service_type or "").strip().lower() == "boat" else "gym",
    }
    if is_phase2_availability_enabled() and (service_type or "").strip().lower() == "boat":
        private_props["set_count"] = str(sc)

    return {
        "summary": resolve_event_summary(
            service_type,
            name,
            set_count=sc,
            telegram_user_id=telegram_user_id,
            booking_id=booking_id,
        ),
        "description": build_event_description(
            phone=phone,
            client_id=client_id,
            workout_id="",
            service_type=service_type,
            booking_id=booking_id,
            name=name,
            telegram_user_id=telegram_user_id,
            set_count=sc,
            duration_min=duration_min,
            start_iso=start_iso,
            end_iso=end_iso,
        ),
        "location": get_calendar_location(service_type),
        "start": {"dateTime": start_iso, "timeZone": tz},
        "end": {"dateTime": end_iso, "timeZone": tz},
        "extendedProperties": {"private": private_props},
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
    set_count: int = 1,
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
        set_count=set_count,
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
            "set_count": max(1, int(set_count or 1)),
        },
    )
    return event_id


def delete_calendar_event_best_effort(event_id: str) -> bool:
    """Best-effort Calendar rollback after partial Sheets failure."""
    eid = (event_id or "").strip()
    if not eid:
        return False
    try:
        from app.services.google import get_google_services

        _, _, calendar_svc = get_google_services()
        calendar_id = current_app.config["GOOGLE_CALENDAR_ID"]
        calendar_svc.events().delete(
            calendarId=calendar_id,
            eventId=eid,
        ).execute(num_retries=2)
        logger.info(
            "booking_calendar_event_deleted",
            extra={"workout_id_tail": eid[-8:]},
        )
        return True
    except Exception as exc:
        logger.error(
            "booking_calendar_event_delete_failed",
            extra={"workout_id_tail": eid[-8:], "error": type(exc).__name__},
        )
        return False
