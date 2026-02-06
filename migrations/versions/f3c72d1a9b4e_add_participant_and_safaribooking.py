"""add participant and safaribooking tables

Revision ID: f3c72d1a9b4e
Revises: e89ecaa2c591
Create Date: 2025-11-17 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f3c72d1a9b4e"
down_revision = "e89ecaa2c591"
branch_labels = None
depends_on = None


def upgrade():
    # Create participant table
    op.create_table(
        "participant",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("level", sa.String(length=50), nullable=True),
        sa.Column("route_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_unique_constraint("uq_participant_email", "participant", ["email"])

    # Create safari_booking table
    op.create_table(
        "safari_booking",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("participant_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("days", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("route_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["participant_id"], ["participant.id"], name="fk_safari_booking_participant"
        ),
    )


def downgrade():
    op.drop_table("safari_booking")
    op.drop_constraint("uq_participant_email", "participant", type_="unique")
    op.drop_table("participant")
