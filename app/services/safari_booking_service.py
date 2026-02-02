"""Service for managing WakeSurfSafari participant and booking flows."""

from __future__ import annotations

from typing import Dict, Any, Optional
from datetime import datetime
import logging

from app.database.models import db, Participant, SafariBooking

logger = logging.getLogger(__name__)


def _upsert_participant(payload: Dict[str, Any]) -> Participant:
    email = (payload.get("email") or "").strip().lower()
    if not email:
        raise ValueError("missing_email")

    participant = Participant.query.filter_by(email=email).first()
    if participant:
        # Update simple fields if provided
        updated = False
        if payload.get("name") and participant.name != payload.get("name"):
            participant.name = payload.get("name")
            updated = True
        if payload.get("phone") and participant.phone != payload.get("phone"):
            participant.phone = payload.get("phone")
            updated = True
        if payload.get("level") and participant.level != payload.get("level"):
            participant.level = payload.get("level")
            updated = True
        if updated:
            db.session.add(participant)
            db.session.commit()
        return participant

    # create
    participant = Participant(
        name=(payload.get("name") or "").strip(),
        email=email,
        phone=(payload.get("phone") or "").strip(),
        level=(payload.get("level") or "").strip(),
        route_id=payload.get("route_id"),
    )
    db.session.add(participant)
    db.session.commit()
    return participant


def create_booking(payload: Dict[str, Any]) -> SafariBooking:
    """Create a safari booking. Expects keys: name, email, phone, startDate, days, level, message

    Returns: SafariBooking object
    Raises: ValueError if validation fails
    """
    # Basic validation
    if not payload.get("startDate"):
        raise ValueError("missing_startDate")
    try:
        start = datetime.strptime(payload.get("startDate"), "%Y-%m-%d").date()
    except Exception:
        raise ValueError("invalid_startDate")

    days = int(payload.get("days") or 1)
    if days < 1 or days > 30:
        raise ValueError("invalid_days")

    # Upsert participant
    participant = _upsert_participant(payload)

    # Create booking
    booking = SafariBooking(
        participant_id=participant.id,
        status="pending",
        start_date=start,
        days=days,
        message=payload.get("message"),
        route_id=payload.get("route_id"),
    )
    db.session.add(booking)
    db.session.commit()

    # Optionally send notification (non-blocking) - use monitoring/notifications in other service
    try:
        from app.services.notifications import notify_admin_new_booking

        notify_admin_new_booking(
            {
                "type": "safari_booking",
                "booking_id": booking.id,
                "participant": {
                    "id": participant.id,
                    "name": participant.name,
                    "email": participant.email,
                },
                "start_date": str(start),
                "days": days,
            }
        )
    except Exception:
        logger.debug("notify_admin_new_booking not available or failed")

    return booking


def get_booking(booking_id: int) -> Optional[SafariBooking]:
    return SafariBooking.query.get(booking_id)


def update_booking(booking_id: int, data: Dict[str, Any]) -> SafariBooking:
    """Update booking fields. Returns updated SafariBooking object.
    Raises: ValueError on validation error or if booking not found.
    """
    b = SafariBooking.query.get(booking_id)
    if not b:
        raise ValueError("not_found")
    # allowed updates: status, message, start_date, days
    if data.get("status"):
        b.status = data.get("status")
    if "message" in data:
        b.message = data.get("message")
    if data.get("startDate"):
        try:
            b.start_date = datetime.strptime(data.get("startDate"), "%Y-%m-%d").date()
        except Exception:
            raise ValueError("invalid_startDate")
    if data.get("days"):
        try:
            b.days = int(data.get("days"))
        except Exception:
            raise ValueError("invalid_days")

    db.session.add(b)
    db.session.commit()
    return b
