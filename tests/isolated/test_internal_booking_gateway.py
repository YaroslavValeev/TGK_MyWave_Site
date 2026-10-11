"""Authenticated HTTP gateway checks against a real temporary booking database."""

import copy
import importlib.util
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
import sqlalchemy as sa
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
SECRET = "isolated-gateway-test-secret-32-characters"
PREFIX = "/api/internal/booking"
CONFIG = {
    "club": {"id": "club_b", "timezone": "Europe/Moscow"},
    "modules": {"booking_boat": True},
    "commercial_booking": {"enabled": False, "provider": "site_internal"},
    "boats": [{"id": "boat_1", "active": True, "slot_minutes": 30, "ride_minutes": 25}],
    "schedules": {
        "season": {"start": "2027-01-01", "end": "2027-12-31"},
        "weekly": {
            key: ["10:00", "10:30", "11:00"]
            for key in (
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
            )
        },
        "overrides": [],
    },
    "cancellation_rules": {
        "cancellation_window_hours": 24,
        "reschedule_window_hours": 24,
    },
}
# Fixtures validate the API inputs; canonical Club Box schema is separately
# exercised in the delivery workspace, rather than duplicated in Site runtime.
SCHEMA = {
    "type": "object",
    "required": list(CONFIG),
    "properties": {
        key: {"type": "array" if key == "boats" else "object"} for key in CONFIG
    },
}
CREATE = {
    "date": "2027-06-01",
    "time": "10:00",
    "client_name": "Demo",
    "client_phone": "79990000001",
    "set_count": 1,
    "internal_id": "tg-request-1",
    "source": "telegram",
    "use_online": False,
}


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    for package in ("app", "app.services", "app.services.booking"):
        stub = ModuleType(package)
        stub.__path__ = [str(ROOT / package.replace(".", "/"))]
        monkeypatch.setitem(sys.modules, package, stub)
    modules = {}
    for name in ("internal_store", "internal_gateway"):
        full = "app.services.booking." + name
        spec = importlib.util.spec_from_file_location(
            full, ROOT / ("app/services/booking/" + name + ".py")
        )
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, full, module)
        spec.loader.exec_module(module)
        modules[name] = module
    supplied = os.getenv("TEST_INTERNAL_BOOKING_DATABASE_URL")
    if supplied:
        url = sa.engine.make_url(supplied)
        if (
            url.get_backend_name() != "postgresql"
            or url.database != "club_box_store_test"
        ):
            pytest.fail("Refusing gateway test outside disposable club_box_store_test")
    else:
        url = "sqlite:///" + str(tmp_path / "gateway.sqlite")
    engine = sa.create_engine(url)
    modules["internal_store"].metadata.create_all(engine)
    gateway = modules["internal_gateway"]
    monkeypatch.setattr(
        gateway, "_utcnow", lambda: datetime(2027, 5, 29, tzinfo=timezone.utc)
    )
    config = copy.deepcopy(CONFIG)

    def client(profile=None):
        app = Flask("isolated_gateway")
        app.register_blueprint(
            gateway.create_internal_booking_blueprint(
                engine, club=profile or config, schema=SCHEMA, secret=SECRET
            )
        )
        return app.test_client()

    env = SimpleNamespace(
        engine=engine,
        store=modules["internal_store"],
        gateway=gateway,
        config=config,
        client=client(),
        client_for=client,
        headers={"X-MyWave-Gateway-Secret": SECRET},
    )
    try:
        yield env
    finally:
        modules["internal_store"].metadata.drop_all(engine)
        engine.dispose()


def create(env, payload=None, client=None):
    return (client or env.client).post(
        PREFIX + "/bookings", json=payload or CREATE, headers=env.headers
    )


def test_unauthorized_requests_do_not_write(runtime):
    env = runtime
    for headers in (
        {},
        {"X-MyWave-Gateway-Secret": "wrong"},
        {"X-MyWave-Gateway-Secret": "неверно"},
    ):
        assert (
            env.client.post(
                PREFIX + "/bookings", json=CREATE, headers=headers
            ).status_code
            == 401
        )
    with env.engine.connect() as connection:
        assert (
            connection.scalar(
                sa.select(sa.func.count()).select_from(env.store.bookings)
            )
            == 0
        )


def test_create_retry_move_cancel_and_slots(runtime):
    env = runtime
    assert (
        env.client.get(PREFIX + "/health", headers=env.headers).json["provider"]
        == "site_internal"
    )
    first = create(env)
    assert first.status_code == 201
    record = first.json["record_id"]
    assert create(env).json["record_id"] == record
    alternate = {**CREATE, "internal_id": "website-request-1", "source": "site"}
    assert create(env, alternate).json["record_id"] == record
    slots = env.client.get(PREFIX + "/slots?date=2027-06-01", headers=env.headers).json[
        "slots"
    ]
    assert slots[0]["available"] is False
    response = env.client.patch(
        PREFIX + "/bookings/" + record,
        json={"datetime": "2027-06-01T10:30:00+03:00", "seance_length": 30},
        headers=env.headers,
    )
    assert response.status_code == 200
    assert response.json["raw"]["time"] == "10:30"
    assert (
        env.client.get(PREFIX + "/bookings/" + record, headers=env.headers).json[
            "record"
        ]["time"]
        == "10:30"
    )
    for _ in range(2):
        assert (
            env.client.post(
                PREFIX + "/bookings/" + record + "/cancel", headers=env.headers
            ).json["status"]
            == "cancelled"
        )
    assert create(env, alternate).json["status"] == "cancelled"


def test_conflict_and_failed_move_preserve_booking(runtime):
    env = runtime
    first = create(env).json["record_id"]
    other = {**CREATE, "internal_id": "other", "client_phone": "+79990000002"}
    assert create(env, other).status_code == 409
    second = create(env, {**other, "time": "10:30"}).json["record_id"]
    assert (
        env.client.patch(
            PREFIX + "/bookings/" + first,
            json={"datetime": "2027-06-01T10:30:00+03:00"},
            headers=env.headers,
        ).status_code
        == 409
    )
    assert (
        env.client.get(PREFIX + "/bookings/" + first, headers=env.headers).json[
            "record"
        ]["time"]
        == "10:00"
    )
    assert second != first


@pytest.mark.parametrize(
    "changes",
    [
        {"date": "2028-06-01"},
        {"date": "not-a-date"},
        {"time": "12:00"},
        {"time": "11:00", "set_count": 2},
        {"set_count": True},
        {"set_count": 11},
        {"client_phone": "tg:1234"},
        {"client_phone": "++79990000001"},
        {"boat_id": "missing"},
    ],
)
def test_invalid_booking_is_rejected(runtime, changes):
    assert create(runtime, {**CREATE, **changes}).status_code == 400


def test_change_windows_and_retry_of_completed_change(runtime, monkeypatch):
    env = runtime
    record = create(env).json["record_id"]
    move = {"datetime": "2027-06-01T10:30:00+03:00", "seance_length": 30}
    assert (
        env.client.patch(
            PREFIX + "/bookings/" + record, json=move, headers=env.headers
        ).status_code
        == 200
    )
    monkeypatch.setattr(
        env.gateway, "_utcnow", lambda: datetime(2027, 6, 1, 6, tzinfo=timezone.utc)
    )
    assert (
        env.client.patch(
            PREFIX + "/bookings/" + record, json=move, headers=env.headers
        ).status_code
        == 200
    )
    assert (
        env.client.patch(
            PREFIX + "/bookings/" + record,
            json={"datetime": "2027-06-01T11:00:00+03:00"},
            headers=env.headers,
        ).status_code
        == 409
    )
    assert (
        env.client.post(
            PREFIX + "/bookings/" + record + "/cancel", headers=env.headers
        ).status_code
        == 409
    )


def test_naive_move_uses_club_timezone(runtime):
    env = runtime
    record = create(env).json["record_id"]
    response = env.client.patch(
        PREFIX + "/bookings/" + record,
        json={"datetime": "2027-06-01T10:30:00", "seance_length": 30},
        headers=env.headers,
    )
    assert response.status_code == 200
    assert response.json["raw"]["datetime"] == "2027-06-01T10:30:00+03:00"


@pytest.mark.parametrize("day", ["2027-03-28", "2027-10-31"])
def test_dst_gap_and_ambiguity_are_rejected(runtime, monkeypatch, day):
    env = runtime
    profile = copy.deepcopy(env.config)
    profile["club"]["timezone"] = "Europe/Berlin"
    profile["schedules"]["weekly"] = {
        name: ["02:30", "03:00"] for name in env.gateway.WEEKDAYS
    }
    monkeypatch.setattr(
        env.gateway, "_utcnow", lambda: datetime(2027, 3, 1, tzinfo=timezone.utc)
    )
    client = env.client_for(profile)
    assert (
        create(env, {**CREATE, "date": day, "time": "02:30"}, client).status_code == 400
    )


def test_multiple_boats_require_explicit_selection(runtime):
    env = runtime
    profile = copy.deepcopy(env.config)
    profile["boats"].append({**profile["boats"][0], "id": "boat_2"})
    client = env.client_for(profile)
    assert create(env, client=client).status_code == 400
    assert create(env, {**CREATE, "boat_id": "boat_2"}, client).status_code == 201


def test_body_limits_and_non_object_json(runtime):
    env = runtime
    assert (
        env.client.post(PREFIX + "/bookings", json=[], headers=env.headers).status_code
        == 400
    )
    assert (
        env.client.post(
            PREFIX + "/bookings", json={"extra": "x" * 65536}, headers=env.headers
        ).status_code
        == 413
    )


def test_cross_club_record_is_inaccessible(runtime):
    env = runtime
    record = create(env).json["record_id"]
    profile = copy.deepcopy(env.config)
    profile["club"]["id"] = "club_c"
    other = env.client_for(profile)
    assert (
        other.get(PREFIX + "/bookings/" + record, headers=env.headers).status_code
        == 404
    )
    assert (
        other.post(
            PREFIX + "/bookings/" + record + "/cancel", headers=env.headers
        ).status_code
        == 404
    )


@pytest.mark.parametrize("missing", ["all", "receipts"])
def test_missing_schema_tables_yields_sanitized_service_error(runtime, missing):
    env = runtime
    if missing == "all":
        env.store.metadata.drop_all(env.engine)
    else:
        env.store.receipts.drop(env.engine)
    response = env.client.get(PREFIX + "/health", headers=env.headers)
    assert response.status_code == 503
    assert response.json == {"ok": False, "error": "booking_storage_unavailable"}


def test_concurrent_move_between_read_and_write_is_not_overwritten(
    runtime, monkeypatch
):
    env = runtime
    record = create(env).json["record_id"]
    original_get = env.store.InternalBookingStore.get

    def racing_get(ledger, booking_id):
        old = original_get(ledger, booking_id)
        # A second real write commits after the HTTP handler reads its baseline.
        ledger.move(
            booking_id,
            boat_id="boat_1",
            start=datetime(2027, 5, 29, 7, tzinfo=timezone.utc),
            duration_minutes=30,
        )
        return old

    with monkeypatch.context() as scoped:
        scoped.setattr(env.store.InternalBookingStore, "get", racing_get)
        response = env.client.patch(
            PREFIX + "/bookings/" + record,
            json={"datetime": "2027-06-01T10:30:00+03:00"},
            headers=env.headers,
        )
    assert response.status_code == 409
    current = env.store.InternalBookingStore(env.engine, "club_b").get(record)
    assert current["start_epoch"] == int(
        datetime(2027, 5, 29, 7, tzinfo=timezone.utc).timestamp()
    )


@pytest.mark.parametrize("change", ["external", "disabled", "overrides", "weak_secret"])
def test_factory_rejects_unsafe_or_unsupported_configuration(runtime, change):
    env = runtime
    profile = copy.deepcopy(env.config)
    secret = SECRET
    if change == "external":
        profile["commercial_booking"]["enabled"] = True
    if change == "disabled":
        profile["modules"]["booking_boat"] = False
    if change == "overrides":
        profile["schedules"]["overrides"] = [{"date": "2027-06-01"}]
    if change == "weak_secret":
        secret = "short"
    with pytest.raises(ValueError):
        env.gateway.create_internal_booking_blueprint(
            env.engine, club=profile, schema=SCHEMA, secret=secret
        )
