"""add unique constraint for booking (date, time, phone)

Revision ID: b2f4a6c8d9e1
Revises: e89ecaa2c591
Create Date: 2025-10-30 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b2f4a6c8d9e1"
down_revision = "e89ecaa2c591"
branch_labels = None
depends_on = None


def upgrade():
    # Create unique constraint to prevent duplicate bookings for same date,time,phone
    with op.batch_alter_table("booking", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_booking_date_time_phone", ["date", "time", "phone"]
        )


def downgrade():
    with op.batch_alter_table("booking", schema=None) as batch_op:
        batch_op.drop_constraint("uq_booking_date_time_phone", type_="unique")
