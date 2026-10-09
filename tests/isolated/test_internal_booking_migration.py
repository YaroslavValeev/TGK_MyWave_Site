"""Real Alembic upgrade/downgrade through Site's env, without Site app/.env.

Only the additive revision is exercised, starting at the preceding Site head.
PostgreSQL runs require a disposable database named club_box_store_test.
"""

import importlib.util
import io
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
PARENT = "d8f1a2b3c4e5"
REVISION = "e6f7a8b9c0d1"


@pytest.fixture
def migration_environment(tmp_path, monkeypatch):
    # Avoid importing Site's heavy __init__ just to load the pure store module.
    for package in ("app", "app.services", "app.services.booking"):
        stub = ModuleType(package)
        stub.__path__ = [str(ROOT / package.replace(".", "/"))]
        monkeypatch.setitem(sys.modules, package, stub)
    spec = importlib.util.spec_from_file_location(
        "app.services.booking.internal_store",
        ROOT / "app/services/booking/internal_store.py",
    )
    store = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, store)
    spec.loader.exec_module(store)
    supplied = os.getenv("TEST_INTERNAL_BOOKING_DATABASE_URL")
    if supplied:
        url = sa.engine.make_url(supplied)
        if (
            url.get_backend_name() != "postgresql"
            or url.database != "club_box_store_test"
        ):
            pytest.fail(
                "Refusing migration test outside disposable club_box_store_test"
            )
    else:
        url = "sqlite:///" + str(tmp_path / "migration.sqlite")
    engine = sa.create_engine(url)
    site_metadata = sa.MetaData()
    legacy = sa.Table(
        "legacy_guard", site_metadata, sa.Column("id", sa.Integer, primary_key=True)
    )
    site_metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(legacy.insert().values(id=1))
    app = Flask("isolated_migration")
    app.extensions["migrate"] = SimpleNamespace(
        db=SimpleNamespace(
            engine=engine, get_engine=lambda: engine, metadatas={None: site_metadata}
        ),
        configure_args={},
    )
    config = Config(str(ROOT / "migrations/alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    # Existing revision files import migrations.migration_utils.
    monkeypatch.syspath_prepend(str(ROOT))
    with app.app_context():
        command.stamp(config, PARENT)
        try:
            yield SimpleNamespace(
                engine=engine, metadata=site_metadata, config=config, store=store
            )
        finally:
            # This fixture is restricted to temporary SQLite/disposable PG only.
            with engine.begin() as connection:
                for name in (
                    "club_box_booking_request",
                    "club_box_booking",
                    "legacy_guard",
                    "alembic_version",
                ):
                    sa.Table(name, sa.MetaData()).drop(connection, checkfirst=True)
            engine.dispose()


def revision(environment):
    with environment.engine.connect() as connection:
        return connection.scalar(sa.text("SELECT version_num FROM alembic_version"))


def booking(environment):
    request = environment.store.BookingRequest(
        boat_id="boat_1",
        start=datetime(2027, 6, 1, 12, tzinfo=timezone.utc),
        duration_minutes=30,
        client_name="Demo",
        client_phone="+79990000001",
        idempotency_key="test-1",
    )
    return environment.store.InternalBookingStore(environment.engine, "club_b").create(
        request
    )


def test_upgrade_matches_store_and_preserves_existing_table(migration_environment):
    env = migration_environment
    command.upgrade(env.config, REVISION)
    assert revision(env) == REVISION
    with env.engine.connect() as connection:
        assert connection.scalar(sa.text("SELECT count(*) FROM legacy_guard")) == 1
        # Actual Site env includes the Core metadata: no spurious DROP or drift.
        assert (
            compare_metadata(MigrationContext.configure(connection), env.metadata) == []
        )
    row = booking(env)
    command.upgrade(env.config, REVISION)
    assert env.store.InternalBookingStore(env.engine, "club_b").get(row["id"]) == row


def test_empty_downgrade_and_reupgrade(migration_environment):
    env = migration_environment
    command.upgrade(env.config, REVISION)
    command.downgrade(env.config, PARENT)
    assert revision(env) == PARENT
    tables = sa.inspect(env.engine).get_table_names()
    assert "club_box_booking" not in tables
    assert "club_box_booking_request" not in tables
    with env.engine.connect() as connection:
        assert connection.scalar(sa.text("SELECT count(*) FROM legacy_guard")) == 1
    command.upgrade(env.config, REVISION)
    assert booking(env)["status"] == "booked"


@pytest.mark.parametrize("cancelled", [False, True])
def test_downgrade_refuses_retained_data_without_schema_changes(
    migration_environment, cancelled
):
    env = migration_environment
    command.upgrade(env.config, REVISION)
    row = booking(env)
    ledger = env.store.InternalBookingStore(env.engine, "club_b")
    if cancelled:
        row = ledger.cancel(row["id"])
    with pytest.raises(RuntimeError, match="downgrade blocked"):
        command.downgrade(env.config, PARENT)
    assert revision(env) == REVISION
    assert ledger.get(row["id"]) == row
    with env.engine.connect() as connection:
        assert (
            connection.scalar(
                sa.select(sa.func.count()).select_from(env.store.receipts)
            )
            == 1
        )


def test_offline_upgrade_sql_and_blocked_offline_downgrade(migration_environment):
    env = migration_environment
    output = io.StringIO()
    env.config.output_buffer = output
    command.upgrade(env.config, PARENT + ":" + REVISION, sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE club_box_booking" in sql
    assert "CREATE TABLE club_box_booking_request" in sql
    assert "CREATE INDEX ix_club_box_booking_occupancy" in sql
    with pytest.raises(RuntimeError, match="online checks"):
        command.downgrade(env.config, REVISION + ":" + PARENT, sql=True)
