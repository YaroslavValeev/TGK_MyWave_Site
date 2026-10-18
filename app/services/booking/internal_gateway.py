"""Opt-in Club Box gateway factory. Not registered by the current Site release."""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
import re
from datetime import date, datetime, time, timedelta, timezone
from functools import wraps
from zoneinfo import ZoneInfo

import jsonschema
from flask import Blueprint, jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.services.booking.internal_store import (
    BookingConflict,
    BookingNotFound,
    BookingRequest,
    InternalBookingStore,
    bookings,
    receipts,
)

WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def _utcnow():
    return datetime.now(timezone.utc)


def _integer(value, minimum, maximum):
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise ValueError("invalid integer")
    return value


def _day(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("date must be YYYY-MM-DD")
    return date.fromisoformat(value)


def _clock(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"(?:[01]\d|2[0-3]):[0-5]\d", value
    ):
        raise ValueError("time must be HH:MM")
    return time.fromisoformat(value)


def _phone(value):
    if not isinstance(value, str) or not re.fullmatch(r"[+0-9 ()-]+", value):
        raise ValueError("invalid phone")
    if value.count("+") > 1 or ("+" in value and not value.strip().startswith("+")):
        raise ValueError("invalid phone")
    digits = re.sub(r"[^0-9]", "", value)
    if not value.strip().startswith("+"):
        if len(digits) == 10:
            digits = "7" + digits
        elif len(digits) == 11 and digits.startswith("8"):
            digits = "7" + digits[1:]
    result = "+" + digits
    if not re.fullmatch(r"\+[1-9][0-9]{6,14}", result):
        raise ValueError("invalid phone")
    return result


def create_internal_booking_blueprint(engine, *, club, schema, secret):
    """Validate a new club and expose authenticated API on a dedicated runtime.

    Caller must register this factory and exempt its blueprint from CSRF because
    every endpoint requires the gateway secret. No .env, schema, table or legacy
    writer is changed here. All old writers must be excluded before activation.
    """
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(club)
    config = copy.deepcopy(club)
    if config["modules"].get("booking_boat") is not True:
        raise ValueError("booking module is disabled")
    commercial = config["commercial_booking"]
    if (
        commercial.get("enabled") is not False
        or commercial.get("provider") != "site_internal"
    ):
        raise ValueError("internal gateway requires external adapter disabled")
    if not isinstance(secret, str) or len(secret) < 32:
        raise ValueError("gateway secret must contain at least 32 characters")
    zone = ZoneInfo(config["club"]["timezone"])
    store = InternalBookingStore(engine, config["club"]["id"])
    schedule = config["schedules"]
    if schedule.get("overrides"):
        raise ValueError("schedule overrides require an explicit adapter")
    season_start = _day(schedule["season"]["start"])
    season_end = _day(schedule["season"]["end"])
    if season_end < season_start:
        raise ValueError("invalid season interval")
    weekly = {key: tuple(schedule["weekly"].get(key, [])) for key in WEEKDAYS}
    for times in weekly.values():
        if not isinstance(times, tuple) or len(set(times)) != len(times):
            raise ValueError("invalid weekly slots")
        for value in times:
            _clock(value)
    boats = {boat["id"]: boat for boat in config["boats"] if boat.get("active") is True}
    if not boats or len({boat["id"] for boat in config["boats"]}) != len(
        config["boats"]
    ):
        raise ValueError("active unique boats required")
    for boat in boats.values():
        _integer(boat["slot_minutes"], 1, 1440)
        _integer(boat["ride_minutes"], 1, boat["slot_minutes"])
    rules = config["cancellation_rules"]
    for key in ("cancellation_window_hours", "reschedule_window_hours"):
        _integer(rules[key], 0, 8760)
    bp = Blueprint(
        "club_box_internal_booking", __name__, url_prefix="/api/internal/booking"
    )

    def protected(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            supplied = request.headers.get("X-MyWave-Gateway-Secret", "")
            if not hmac.compare_digest(supplied.encode(), secret.encode()):
                return jsonify(ok=False, error="unauthorized"), 401
            if request.content_length and request.content_length > 65536:
                return jsonify(ok=False, error="request_too_large"), 413
            try:
                return function(*args, **kwargs)
            except BookingNotFound:
                return jsonify(ok=False, error="booking_not_found"), 404
            except BookingConflict:
                return jsonify(ok=False, error="booking_conflict"), 409
            except (ValueError, TypeError, KeyError, OverflowError):
                return jsonify(ok=False, error="invalid_request"), 400
            except SQLAlchemyError:
                # Do not return SQL errors, DSNs, query arguments or PII.
                return jsonify(ok=False, error="booking_storage_unavailable"), 503

        return wrapper

    def body():
        value = request.get_json(silent=True)
        if not isinstance(value, dict):
            raise ValueError("JSON object required")
        return value

    def boat_id(value=None):
        if value is None and len(boats) == 1:
            return next(iter(boats))
        if not isinstance(value, str) or value not in boats:
            raise ValueError("active boat required")
        return value

    def slot(day_value, clock_value, boat, count):
        day = _day(day_value)
        local_time = _clock(clock_value)
        _integer(count, 1, 10)
        if not season_start <= day <= season_end:
            raise ValueError("outside season")
        allowed = weekly[WEEKDAYS[day.weekday()]]
        naive = datetime.combine(day, local_time)
        candidates = [naive.replace(tzinfo=zone, fold=fold) for fold in (0, 1)]
        valid = [
            candidate
            for candidate in candidates
            if candidate.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None)
            == naive
        ]
        if not valid or (
            len(valid) == 2 and valid[0].utcoffset() != valid[1].utcoffset()
        ):
            raise ValueError("ambiguous or nonexistent local time")
        start = valid[0].astimezone(timezone.utc)
        if start <= _utcnow():
            raise ValueError("past slot")
        minutes = boats[boat]["slot_minutes"]
        for number in range(count):
            position = (start + timedelta(minutes=minutes * number)).astimezone(zone)
            if position.date() != day or position.strftime("%H:%M") not in allowed:
                raise ValueError("outside configured slot grid")
        return start, minutes * count

    def editable(row, rule):
        if _utcnow().timestamp() > row["start_epoch"] - rules[rule] * 3600:
            raise BookingConflict("change window closed")

    def wire(row):
        start = datetime.fromtimestamp(row["start_epoch"], timezone.utc).astimezone(
            zone
        )
        return {
            "id": row["id"],
            "record_id": row["id"],
            "status": row["status"],
            "boat_id": row["boat_id"],
            "date": start.date().isoformat(),
            "time": start.strftime("%H:%M"),
            "datetime": start.isoformat(),
            "seance_length": row["end_epoch"] - row["start_epoch"],
            "duration_minutes": (row["end_epoch"] - row["start_epoch"]) // 60,
        }

    @bp.get("/health")
    @protected
    def health():
        # Check schema availability rather than treating configured DB as healthy.
        with engine.connect() as connection:
            connection.execute(select(bookings).limit(0))
            connection.execute(select(receipts).limit(0))
        return jsonify(
            ok=True, provider="site_internal", enabled=True, read=True, write=True
        )

    @bp.get("/slots")
    @protected
    def slots():
        day = _day(request.args.get("date"))
        boat = boat_id(request.args.get("boat_id"))
        result = []
        for value in weekly[WEEKDAYS[day.weekday()]]:
            try:
                start, duration = slot(day.isoformat(), value, boat, 1)
            except ValueError:
                continue
            result.append(
                {
                    "start_time": value,
                    "duration_minutes": duration,
                    "available": store.available(
                        boat_id=boat, start=start, duration_minutes=duration
                    ),
                }
            )
        return jsonify(ok=True, date=day.isoformat(), slots=result)

    @bp.post("/bookings")
    @protected
    def create():
        data = body()
        if data.get("service_type", "boat") != "boat":
            raise ValueError("boat booking required")
        boat = boat_id(data.get("boat_id"))
        start, duration = slot(
            data.get("date"), data.get("time"), boat, data.get("set_count", 1)
        )
        phone = _phone(data.get("client_phone"))
        name = data.get("client_name")
        key = data.get("internal_id") or request.headers.get("Idempotency-Key")
        if not key:
            # Stable across retries and interfaces; fresh rebooking after cancel
            # needs an explicit new internal_id/Idempotency-Key.
            key = hashlib.sha256(
                json.dumps([boat, start.isoformat(), duration, phone, name]).encode()
            ).hexdigest()
        row = store.create(BookingRequest(boat, start, duration, name, phone, key))
        return (
            jsonify(ok=True, record_id=row["id"], status=row["status"], raw=wire(row)),
            201,
        )

    @bp.get("/bookings/<record_id>")
    @protected
    def get(record_id):
        return jsonify(ok=True, record=wire(store.get(record_id)))

    @bp.patch("/bookings/<record_id>")
    @protected
    def move(record_id):
        data = body()
        row = store.get(record_id)
        boat = boat_id(data.get("boat_id", row["boat_id"]))
        supplied = data.get("datetime")
        if not isinstance(supplied, str):
            raise ValueError("datetime required")
        target = datetime.fromisoformat(supplied)
        if target.second or target.microsecond:
            raise ValueError("minute alignment required")
        # Legacy gateway clients may send a local ISO datetime without offset.
        # Interpret it only through the configured club zone; slot() rejects
        # ambiguous/nonexistent local times instead of guessing a DST fold.
        local = target if target.tzinfo is None else target.astimezone(zone)
        # The real Telegram gateway client uses legacy seance_length seconds.
        # Keep the storage API in minutes and reject ambiguous partial minutes.
        seconds = data.get("seance_length", row["end_epoch"] - row["start_epoch"])
        _integer(seconds, 1, 86400)
        if seconds % 60:
            raise ValueError("whole-minute duration required")
        duration = seconds // 60
        step = boats[boat]["slot_minutes"]
        if duration % step:
            raise ValueError("duration must include whole occupancy slots")
        start, duration = slot(
            local.date().isoformat(), local.strftime("%H:%M"), boat, duration // step
        )
        before = (row["boat_id"], row["start_epoch"], row["end_epoch"], row["status"])

        def validate_move(current):
            actual = (
                current["boat_id"],
                current["start_epoch"],
                current["end_epoch"],
                current["status"],
            )
            if actual != before:
                raise BookingConflict("booking changed; reload before moving")
            editable(current, "reschedule_window_hours")

        moved = store.move(
            record_id,
            boat_id=boat,
            start=start,
            duration_minutes=duration,
            validator=validate_move,
        )
        return jsonify(
            ok=True, record_id=record_id, status=moved["status"], raw=wire(moved)
        )

    @bp.post("/bookings/<record_id>/cancel")
    @protected
    def cancel(record_id):
        cancelled = store.cancel(
            record_id,
            validator=lambda current: editable(current, "cancellation_window_hours"),
        )
        return jsonify(ok=True, record_id=record_id, status=cancelled["status"])

    return bp
