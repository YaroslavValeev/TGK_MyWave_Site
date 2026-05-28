"""Web booking idempotency checks."""

from __future__ import annotations

import uuid

from flask import current_app

from app.services.booking.phone import normalize_phone
from app.services.google_sheets_service import read_records


def generate_booking_id() -> str:
    return f"bk_{uuid.uuid4().hex[:12]}"


def is_duplicate_web_booking(
    phone: str,
    date: str,
    time: str,
    service_type: str,
) -> bool:
    """phone + date + time + service_type in Client_Workouts."""
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
    svc = (service_type or "").strip().lower()
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
        if (
            row_date == date
            and row_time == time[:5]
            and (not svc or not row_svc or row_svc == svc)
        ):
            status = (row.get("status") or "").strip().lower()
            if status in ("", "booked", "подтверждено", "confirmed", "new", "pending"):
                return True
    return False
