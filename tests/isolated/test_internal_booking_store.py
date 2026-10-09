"""Real transactional ledger tests; no Site app, external APIs or production env.

SQLite is the default. A disposable PostgreSQL database may be supplied through
TEST_INTERNAL_BOOKING_DATABASE_URL, with database name club_box_store_test.
"""

import importlib.util
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url

SOURCE = Path(__file__).resolve().parents[2] / "app/services/booking/internal_store.py"
SPEC = importlib.util.spec_from_file_location("isolated_internal_store", SOURCE)
store_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = store_module
SPEC.loader.exec_module(store_module)


@pytest.fixture
def engine(tmp_path):
    supplied = os.getenv("TEST_INTERNAL_BOOKING_DATABASE_URL")
    if supplied:
        url = make_url(supplied)
        if (
            url.get_backend_name() != "postgresql"
            or url.database != "club_box_store_test"
        ):
            pytest.fail(
                "Refusing to alter a database other than disposable club_box_store_test"
            )
    else:
        url = "sqlite:///" + str(tmp_path / "club-b.sqlite")
    engine = create_engine(url)
    store_module.metadata.create_all(engine)
    try:
        yield engine
    finally:
        store_module.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def ledger(engine):
    return store_module.InternalBookingStore(engine, "club_b")


@pytest.fixture
def request_data():
    return store_module.BookingRequest(
        boat_id="boat_1",
        start=datetime(2027, 6, 1, 12, tzinfo=timezone.utc),
        duration_minutes=30,
        client_name="Demo Owner",
        client_phone="+79990000001",
        idempotency_key="website-request-1",
    )


def test_create_retry_and_cross_interface_duplicate(ledger, request_data, engine):
    first = ledger.create(request_data)
    assert ledger.create(request_data)["id"] == first["id"]
    second_interface = replace(request_data, idempotency_key="telegram-request-1")
    assert ledger.create(second_interface)["id"] == first["id"]
    with engine.connect() as connection:
        assert (
            connection.scalar(select(func.count()).select_from(store_module.bookings))
            == 1
        )
        assert (
            connection.scalar(select(func.count()).select_from(store_module.receipts))
            == 2
        )


def test_changed_payload_for_existing_key_rejected(ledger, request_data):
    ledger.create(request_data)
    with pytest.raises(store_module.BookingConflict, match="payload changed"):
        ledger.create(replace(request_data, client_phone="+79990000002"))


def test_overlapping_slot_rejected_and_adjacent_slot_allowed(ledger, request_data):
    ledger.create(request_data)
    with pytest.raises(store_module.BookingConflict, match="occupied"):
        ledger.create(
            replace(
                request_data,
                start=request_data.start + timedelta(minutes=15),
                client_phone="+79990000002",
                idempotency_key="overlap",
            )
        )
    following = ledger.create(
        replace(
            request_data,
            start=request_data.start + timedelta(minutes=30),
            idempotency_key="adjacent",
        )
    )
    assert following["status"] == "booked"


def test_move_cancel_and_freed_slot(ledger, request_data):
    first = ledger.create(request_data)
    moved = ledger.move(
        first["id"],
        boat_id="boat_1",
        start=request_data.start + timedelta(hours=1),
        duration_minutes=30,
    )
    assert moved["id"] == first["id"]
    assert ledger.available(
        boat_id="boat_1", start=request_data.start, duration_minutes=30
    )
    assert not ledger.available(
        boat_id="boat_1",
        start=request_data.start + timedelta(hours=1),
        duration_minutes=30,
    )
    assert ledger.cancel(first["id"])["status"] == "cancelled"
    assert ledger.cancel(first["id"])["status"] == "cancelled"
    assert ledger.available(
        boat_id="boat_1",
        start=request_data.start + timedelta(hours=1),
        duration_minutes=30,
    )
    assert ledger.create(request_data)["status"] == "cancelled"
    assert (
        ledger.create(replace(request_data, idempotency_key="new-after-cancel"))["id"]
        != first["id"]
    )


def test_cross_interface_receipt_survives_move_and_cancel(ledger, request_data):
    row = ledger.create(request_data)
    alternate = replace(request_data, idempotency_key="telegram-create")
    ledger.create(alternate)
    ledger.move(
        row["id"], boat_id="boat_2", start=request_data.start, duration_minutes=60
    )
    ledger.cancel(row["id"])
    assert ledger.create(alternate)["id"] == row["id"]
    assert ledger.create(alternate)["status"] == "cancelled"
    with pytest.raises(store_module.BookingConflict):
        ledger.create(replace(alternate, duration_minutes=60))


def test_failed_move_preserves_original_booking(ledger, request_data):
    first = ledger.create(request_data)
    ledger.create(replace(request_data, boat_id="boat_2", idempotency_key="second"))
    with pytest.raises(store_module.BookingConflict):
        ledger.move(
            first["id"], boat_id="boat_2", start=request_data.start, duration_minutes=30
        )
    assert ledger.get(first["id"]) == first


def test_cancelled_booking_cannot_be_moved(ledger, request_data):
    row = ledger.create(request_data)
    ledger.cancel(row["id"])
    with pytest.raises(store_module.BookingConflict, match="cancelled"):
        ledger.move(
            row["id"], boat_id="boat_2", start=request_data.start, duration_minutes=30
        )


def test_clubs_and_boats_are_isolated(ledger, engine, request_data):
    row = ledger.create(request_data)
    other = store_module.InternalBookingStore(engine, "club_c")
    assert other.create(request_data)["id"] != row["id"]
    assert (
        ledger.create(
            replace(request_data, boat_id="boat_2", idempotency_key="boat-2")
        )["id"]
        != row["id"]
    )
    for operation in (other.get, other.cancel):
        with pytest.raises(store_module.BookingNotFound):
            operation(row["id"])


def test_timezone_equivalent_request_is_idempotent(ledger, request_data):
    row = ledger.create(request_data)
    other = replace(
        request_data, start=request_data.start.astimezone(timezone(timedelta(hours=3)))
    )
    assert ledger.create(other)["id"] == row["id"]


def test_booking_persists_across_store_instances(engine, request_data):
    first = store_module.InternalBookingStore(engine, "club_b").create(request_data)
    assert store_module.InternalBookingStore(engine, "club_b").get(first["id"]) == first


def test_concurrent_same_key_creates_one_booking(engine, request_data):
    barrier = Barrier(4)

    def create(_):
        barrier.wait(timeout=10)
        return store_module.InternalBookingStore(engine, "club_b").create(request_data)[
            "id"
        ]

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(create, range(4)))
    assert len(set(results)) == 1


def test_concurrent_distinct_clients_cannot_double_book(engine, request_data):
    barrier = Barrier(2)

    def create(number):
        store = store_module.InternalBookingStore(engine, "club_b")
        barrier.wait(timeout=10)
        try:
            store.create(
                replace(
                    request_data,
                    client_phone=f"+7999000000{number}",
                    idempotency_key=f"request-{number}",
                )
            )
            return "booked"
        except store_module.BookingConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(create, (1, 2))) == ["booked", "conflict"]


@pytest.mark.parametrize("isolation", ["AUTOCOMMIT", "REPEATABLE READ"])
def test_inherited_isolation_does_not_bypass_writer_lock(
    engine, request_data, isolation
):
    if isolation == "REPEATABLE READ" and engine.dialect.name == "sqlite":
        pytest.skip("SQLite has no REPEATABLE READ isolation option")
    configured = engine.execution_options(isolation_level=isolation)
    barrier = Barrier(2)

    def create(number):
        ledger = store_module.InternalBookingStore(configured, "club_b")
        barrier.wait(timeout=10)
        try:
            ledger.create(
                replace(
                    request_data,
                    client_phone=f"+7999000000{number}",
                    idempotency_key=f"request-{number}",
                )
            )
            return "booked"
        except store_module.BookingConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(create, (1, 2))) == ["booked", "conflict"]


@pytest.mark.parametrize(
    "changes",
    [
        {"start": datetime(2027, 6, 1, 12)},
        {"duration_minutes": 0},
        {"duration_minutes": True},
        {"duration_minutes": 1441},
        {"client_phone": "89990000001"},
        {"client_name": ""},
        {"idempotency_key": ""},
        {"boat_id": "../boat"},
    ],
)
def test_invalid_request_does_not_write(ledger, request_data, engine, changes):
    with pytest.raises(ValueError):
        ledger.create(replace(request_data, **changes))
    with engine.connect() as connection:
        assert (
            connection.scalar(select(func.count()).select_from(store_module.bookings))
            == 0
        )
