"""Add Club Box booking and request receipts without activating a provider.

Revision ID: e6f7a8b9c0d1
Revises: d8f1a2b3c4e5
"""

from alembic import context, op
import sqlalchemy as sa

revision = "e6f7a8b9c0d1"
down_revision = "d8f1a2b3c4e5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "club_box_booking",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("club_id", sa.String(64), nullable=False),
        sa.Column("boat_id", sa.String(64), nullable=False),
        sa.Column("start_epoch", sa.BigInteger(), nullable=False),
        sa.Column("end_epoch", sa.BigInteger(), nullable=False),
        sa.Column("client_name", sa.String(200), nullable=False),
        sa.Column("client_phone", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.UniqueConstraint("club_id", "id", name="uq_club_box_booking_identity"),
        sa.CheckConstraint(
            "end_epoch > start_epoch", name="ck_club_box_booking_interval"
        ),
        sa.CheckConstraint(
            "status IN ('booked', 'cancelled')", name="ck_club_box_booking_status"
        ),
    )
    op.create_index(
        "ix_club_box_booking_occupancy",
        "club_box_booking",
        ["club_id", "boat_id", "status", "start_epoch"],
    )
    op.create_table(
        "club_box_booking_request",
        sa.Column("club_id", sa.String(64), primary_key=True),
        sa.Column("idempotency_key", sa.String(128), primary_key=True),
        sa.Column("booking_id", sa.String(32), nullable=False),
        sa.Column("request_sha256", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(
            ["club_id", "booking_id"],
            ["club_box_booking.club_id", "club_box_booking.id"],
        ),
    )


def downgrade():
    if context.is_offline_mode():
        raise RuntimeError(
            "Club Box downgrade requires online checks for retained booking data"
        )
    connection = op.get_bind()
    if connection.dialect.name == "postgresql":
        connection.exec_driver_sql(
            "LOCK TABLE club_box_booking, club_box_booking_request IN ACCESS EXCLUSIVE MODE"
        )
    elif connection.dialect.name == "sqlite":
        # Acquire the database writer lock without changing rows. This also
        # starts SQLite's real transaction before the checks and DDL.
        connection.exec_driver_sql(
            "UPDATE club_box_booking SET status=status WHERE 1=0"
        )
    else:
        raise RuntimeError("Club Box downgrade supports SQLite and PostgreSQL only")
    # Check both tables before any DROP; cancelled bookings and receipts matter too.
    for name in ("club_box_booking", "club_box_booking_request"):
        table = sa.table(name, sa.column("club_id"))
        if connection.execute(sa.select(table.c.club_id).limit(1)).first() is not None:
            raise RuntimeError(
                "Club Box downgrade blocked: retain/export booking data before schema removal"
            )
    op.drop_table("club_box_booking_request")
    op.drop_index("ix_club_box_booking_occupancy", table_name="club_box_booking")
    op.drop_table("club_box_booking")
