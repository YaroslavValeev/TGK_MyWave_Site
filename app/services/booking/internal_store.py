"""Transactional Club Box booking storage; routes and schema migration are separate.

Callers supply the existing Site engine. Only SQLite and PostgreSQL are supported.
No tables are created on import or first use. Dates must include a UTC offset;
calendar/CRM/notifications are deliberately outside the storage transaction.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    ForeignKeyConstraint,
    Index,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    select,
    text,
)
from sqlalchemy.engine import Engine

metadata = MetaData()
bookings = Table(
    "club_box_booking",
    metadata,
    Column("id", String(32), primary_key=True),
    Column("club_id", String(64), nullable=False),
    Column("boat_id", String(64), nullable=False),
    Column("start_epoch", BigInteger, nullable=False),
    Column("end_epoch", BigInteger, nullable=False),
    Column("client_name", String(200), nullable=False),
    Column("client_phone", String(16), nullable=False),
    Column("status", String(16), nullable=False),
    UniqueConstraint("club_id", "id", name="uq_club_box_booking_identity"),
    CheckConstraint("end_epoch > start_epoch", name="ck_club_box_booking_interval"),
    CheckConstraint(
        "status IN ('booked', 'cancelled')", name="ck_club_box_booking_status"
    ),
    Index(
        "ix_club_box_booking_occupancy", "club_id", "boat_id", "status", "start_epoch"
    ),
)
receipts = Table(
    "club_box_booking_request",
    metadata,
    Column("club_id", String(64), primary_key=True),
    Column("idempotency_key", String(128), primary_key=True),
    Column("booking_id", String(32), nullable=False),
    Column("request_sha256", String(64), nullable=False),
    ForeignKeyConstraint(
        ["club_id", "booking_id"],
        ["club_box_booking.club_id", "club_box_booking.id"],
    ),
)


class BookingConflict(ValueError):
    """The boat is occupied or an idempotency key has another payload."""


class BookingNotFound(LookupError):
    """A booking does not belong to this club."""


@dataclass(frozen=True)
class BookingRequest:
    boat_id: str
    start: datetime
    duration_minutes: int
    client_name: str
    client_phone: str
    idempotency_key: str


def _identifier(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value):
        raise ValueError("invalid club or boat identifier")
    return value


def _interval(start: datetime, duration: int) -> tuple[int, int]:
    if (
        not isinstance(start, datetime)
        or start.tzinfo is None
        or start.utcoffset() is None
    ):
        raise ValueError("booking start must have a UTC offset")
    if start.second or start.microsecond:
        raise ValueError("booking start must align to a minute")
    if (
        isinstance(duration, bool)
        or not isinstance(duration, int)
        or not 1 <= duration <= 1440
    ):
        raise ValueError("duration must be between 1 and 1440 minutes")
    epoch = int(start.timestamp())
    return epoch, epoch + duration * 60


class InternalBookingStore:
    """Single occupancy ledger, scoped to a club; one booking occupies one boat.

    All writers MUST use this store. PostgreSQL locks serialize operations per
    club; SQLite uses BEGIN IMMEDIATE. Adjacent intervals do not conflict.
    Club hours, pricing, authorization and allowed boats belong in the API layer.
    """

    def __init__(self, engine: Engine, club_id: str):
        if engine.dialect.name not in ("sqlite", "postgresql"):
            raise ValueError("internal booking requires SQLite or PostgreSQL")
        self.engine = engine
        self.club_id = _identifier(club_id)

    @contextmanager
    def _write(self):
        with self.engine.connect() as connection:
            try:
                if self.engine.dialect.name == "sqlite":
                    connection = connection.execution_options(
                        isolation_level="SERIALIZABLE"
                    )
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                else:
                    # Read fresh state after waiting for another writer's lock;
                    # inherited REPEATABLE READ/AUTOCOMMIT must not defeat it.
                    connection = connection.execution_options(
                        isolation_level="READ COMMITTED"
                    )
                    connection.begin()
                    # Lock the club, including moves between boats, in one order.
                    digest = hashlib.sha256(
                        ("club_box_booking:" + self.club_id).encode()
                    ).digest()
                    lock_id = int.from_bytes(digest[:8], "big", signed=True)
                    connection.execute(
                        text("SELECT pg_advisory_xact_lock(:lock_id)"),
                        {"lock_id": lock_id},
                    )
                yield connection
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def _find(self, connection, booking_id):
        row = (
            connection.execute(
                select(bookings).where(
                    bookings.c.club_id == self.club_id, bookings.c.id == booking_id
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise BookingNotFound("booking not found")
        return dict(row)

    def _occupied(self, connection, boat_id, start, end, *, exclude=None):
        query = select(bookings.c.id).where(
            bookings.c.club_id == self.club_id,
            bookings.c.boat_id == boat_id,
            bookings.c.status == "booked",
            bookings.c.start_epoch < end,
            bookings.c.end_epoch > start,
        )
        if exclude:
            query = query.where(bookings.c.id != exclude)
        return connection.execute(query.limit(1)).first() is not None

    def create(self, request: BookingRequest) -> dict:
        boat = _identifier(request.boat_id)
        start, end = _interval(request.start, request.duration_minutes)
        if not isinstance(request.client_name, str):
            raise ValueError("client name must be a string")
        name = request.client_name.strip()
        if not name or len(name) > 200:
            raise ValueError("client name is required (maximum 200 characters)")
        if not isinstance(request.client_phone, str) or not re.fullmatch(
            r"\+[1-9][0-9]{6,14}", request.client_phone
        ):
            raise ValueError("client phone must be normalized E.164")
        key = request.idempotency_key
        if not isinstance(key, str) or not key.strip() or len(key) > 128:
            raise ValueError("idempotency key is required (maximum 128 characters)")
        payload = {
            "boat_id": boat,
            "start_epoch": start,
            "end_epoch": end,
            "client_name": name,
            "client_phone": request.client_phone,
        }
        fingerprint = hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        with self._write() as connection:
            previous = (
                connection.execute(
                    select(receipts).where(
                        receipts.c.club_id == self.club_id,
                        receipts.c.idempotency_key == key,
                    )
                )
                .mappings()
                .first()
            )
            if previous:
                if previous["request_sha256"] != fingerprint:
                    raise BookingConflict("idempotency key payload changed")
                return self._find(connection, previous["booking_id"])
            # Two interfaces may supply different keys for the same booking.
            duplicate = (
                connection.execute(
                    select(bookings).where(
                        bookings.c.club_id == self.club_id,
                        bookings.c.boat_id == boat,
                        bookings.c.start_epoch == start,
                        bookings.c.end_epoch == end,
                        bookings.c.client_phone == request.client_phone,
                        bookings.c.status == "booked",
                    )
                )
                .mappings()
                .first()
            )
            if duplicate:
                connection.execute(
                    receipts.insert().values(
                        club_id=self.club_id,
                        idempotency_key=key,
                        booking_id=duplicate["id"],
                        request_sha256=fingerprint,
                    )
                )
                return dict(duplicate)
            if self._occupied(connection, boat, start, end):
                raise BookingConflict("boat slot occupied")
            row = {
                **payload,
                "id": uuid.uuid4().hex,
                "club_id": self.club_id,
                "status": "booked",
            }
            connection.execute(bookings.insert().values(**row))
            connection.execute(
                receipts.insert().values(
                    club_id=self.club_id,
                    idempotency_key=key,
                    booking_id=row["id"],
                    request_sha256=fingerprint,
                )
            )
            return row

    def get(self, booking_id: str) -> dict:
        with self.engine.connect() as connection:
            return self._find(connection, booking_id)

    def move(
        self, booking_id: str, *, boat_id: str, start: datetime, duration_minutes: int
    ) -> dict:
        boat = _identifier(boat_id)
        begin, end = _interval(start, duration_minutes)
        with self._write() as connection:
            row = self._find(connection, booking_id)
            if row["status"] != "booked":
                raise BookingConflict("cancelled booking cannot be moved")
            if self._occupied(connection, boat, begin, end, exclude=booking_id):
                raise BookingConflict("boat slot occupied")
            connection.execute(
                bookings.update()
                .where(bookings.c.id == booking_id)
                .values(boat_id=boat, start_epoch=begin, end_epoch=end)
            )
            return self._find(connection, booking_id)

    def cancel(self, booking_id: str) -> dict:
        with self._write() as connection:
            self._find(connection, booking_id)
            connection.execute(
                bookings.update()
                .where(bookings.c.id == booking_id)
                .values(status="cancelled")
            )
            return self._find(connection, booking_id)

    def available(
        self, *, boat_id: str, start: datetime, duration_minutes: int
    ) -> bool:
        boat = _identifier(boat_id)
        begin, end = _interval(start, duration_minutes)
        with self.engine.connect() as connection:
            return not self._occupied(connection, boat, begin, end)
