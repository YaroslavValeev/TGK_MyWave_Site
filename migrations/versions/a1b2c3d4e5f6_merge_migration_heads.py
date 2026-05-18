"""merge migration heads (booking/images + safari participant)

Revision ID: a1b2c3d4e5f6
Revises: b2a005fd0c4b, f3c72d1a9b4e
Create Date: 2026-05-19

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = ("b2a005fd0c4b", "f3c72d1a9b4e")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
