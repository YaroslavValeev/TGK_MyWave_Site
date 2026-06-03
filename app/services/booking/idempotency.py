"""Web booking idempotency checks."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from flask import current_app

from app.config.booking_durations import BOAT_SET_MINUTES, GYM_SLOT_MINUTES
from app.config.booking_features import is_phase2_availability_enabled
from app.services.booking.phone import normalize_phone
from app.services.google_sheets_service import read_records


def generate_booking_id() -> str:
    return f"bk_{uuid.uuid4().hex[:12]}"


def _add_minutes_to_time(date_str: str, time_str: str, minutes: int) -> str:
    start = datetime.strptime(f"{date_str} {time_str[:5]}", "%Y-%m-%d %H:%M")
    end = start + timedelta(minutes=minutes)
    return end.strftime("%H:%M")


def _row_start_end(
    row_date: str,
    row_time: str,
    *,
    duration_min: int,
) -> tuple[str, str]:
    start = row_time[:5]
    end = _add_minutes_to_time(row_date, start, duration_min)
    return start, end


def _range_duration_minutes(service_type: str, set_count: int) -> int:
    svc = (service_type or "gym").strip().lower()
    if svc == "boat":
        return BOAT_SET_MINUTES * max(1, int(set_count or 1))
    if svc == "gym":
        return GYM_SLOT_MINUTES
    return GYM_SLOT_MINUTES


def is_duplicate_web_booking(
    phone: str,
    date: str,
    time: str,
    service_type: str,
    *,
    set_count: int = 1,
) -> bool:
    """
    Phase 1: phone + date + start time + service_type.
    Phase 2 (availability flag ON): same + continuous end time (range key).
    """
    normalized = normalize_phone(phone)
    if not normalized:
        return False

    sid = current_app.config["SPREADSHEET_ID"]
    clients = read_records(sid, "Clients")
    client_ids = {
        c.get("client_id")
        for c in clients
        if normalize_phone(c.get("phone") or "") == normalized and c.get("client_id")
    }
    if not client_ids:
        return False

    bookings = read_records(sid, "Client_Workouts")
    workouts = read_records(sid, "Workouts")
    workout_type_by_id = {
        str(w.get("workout_id") or ""): (w.get("workout_type") or "").strip().lower()
        for w in workouts
        if w.get("workout_id")
    }
    duration_by_id = {
        str(w.get("workout_id") or ""): int(w.get("duration") or 0)
        for w in workouts
        if w.get("workout_id")
    }

    svc = (service_type or "").strip().lower()
    time_norm = time.strip()[:5]
    use_range = is_phase2_availability_enabled()
    if use_range:
        cand_duration = _range_duration_minutes(svc, set_count)
        _, cand_end = _row_start_end(date, time_norm, duration_min=cand_duration)

    for row in bookings:
        if row.get("client_id") not in client_ids:
            continue
        row_date = (row.get("date") or "").strip()
        row_time = (row.get("time") or "").strip()
        if not row_date and row.get("date_time"):
            parts = str(row.get("date_time")).split()
            if len(parts) >= 2:
                row_date, row_time = parts[0], parts[1][:5]
        wid = str(row.get("workout_id") or "")
        row_svc = (
            row.get("service_type") or ""
        ).strip().lower() or workout_type_by_id.get(wid, "")
        if row_date != date or row_time[:5] != time_norm:
            continue
        if svc and row_svc and row_svc != svc:
            continue

        status = (row.get("status") or "").strip().lower()
        if status not in ("", "booked", "подтверждено", "confirmed", "new", "pending"):
            continue

        if not use_range:
            return True

        raw_dur = duration_by_id.get(wid) or 0
        row_duration = raw_dur or _range_duration_minutes(row_svc or svc, 1)
        _, row_end = _row_start_end(
            row_date,
            row_time[:5],
            duration_min=row_duration,
        )
        if row_end == cand_end:
            return True

    return False
