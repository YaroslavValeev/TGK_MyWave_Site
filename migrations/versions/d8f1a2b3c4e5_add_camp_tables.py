"""add camp catalog tables

Revision ID: d8f1a2b3c4e5
Revises: c4e8f1a2b3d0
Create Date: 2026-07-07

"""
from alembic import op
import sqlalchemy as sa

from migrations.migration_utils import table_names


revision = "d8f1a2b3c4e5"
down_revision = "c4e8f1a2b3d0"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    tables = table_names(conn)

    if "camp" not in tables:
        op.create_table(
            "camp",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("source_system", sa.String(length=32), nullable=False),
            sa.Column("external_id", sa.String(length=128), nullable=True),
            sa.Column("source_url", sa.Text(), nullable=True),
            sa.Column("title", sa.String(length=320), nullable=False),
            sa.Column("slug", sa.String(length=320), nullable=False),
            sa.Column("short_description", sa.Text(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("sport", sa.String(length=32), nullable=False),
            sa.Column("level", sa.String(length=32), nullable=False),
            sa.Column("country", sa.String(length=128), nullable=True),
            sa.Column("region", sa.String(length=128), nullable=True),
            sa.Column("city", sa.String(length=128), nullable=True),
            sa.Column("location_name", sa.String(length=256), nullable=True),
            sa.Column("address", sa.Text(), nullable=True),
            sa.Column("lat", sa.Float(), nullable=True),
            sa.Column("lng", sa.Float(), nullable=True),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("duration_days", sa.Integer(), nullable=True),
            sa.Column("price_from", sa.Integer(), nullable=True),
            sa.Column("price_to", sa.Integer(), nullable=True),
            sa.Column("currency", sa.String(length=8), nullable=False),
            sa.Column("price_note", sa.Text(), nullable=True),
            sa.Column("included", sa.Text(), nullable=True),
            sa.Column("not_included", sa.Text(), nullable=True),
            sa.Column("organizer_name", sa.String(length=256), nullable=True),
            sa.Column("organizer_type", sa.String(length=32), nullable=False),
            sa.Column("booking_url", sa.Text(), nullable=True),
            sa.Column("lead_form_enabled", sa.Boolean(), nullable=False),
            sa.Column("cover_image_url", sa.Text(), nullable=True),
            sa.Column("gallery", sa.JSON(), nullable=True),
            sa.Column("video_url", sa.Text(), nullable=True),
            sa.Column("content_rights_status", sa.String(length=32), nullable=False),
            sa.Column("publication_status", sa.String(length=32), nullable=False),
            sa.Column("availability_status", sa.String(length=32), nullable=False),
            sa.Column("priority", sa.Integer(), nullable=False),
            sa.Column("is_featured", sa.Boolean(), nullable=False),
            sa.Column("is_owner_camp", sa.Boolean(), nullable=False),
            sa.Column("seo_title", sa.String(length=320), nullable=True),
            sa.Column("seo_description", sa.Text(), nullable=True),
            sa.Column("seo_h1", sa.String(length=320), nullable=True),
            sa.Column("canonical_url", sa.Text(), nullable=True),
            sa.Column("robots_index", sa.Boolean(), nullable=False),
            sa.Column("source_payload", sa.JSON(), nullable=True),
            sa.Column("site_overrides", sa.JSON(), nullable=True),
            sa.Column("duplicate_of_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("source_updated_at", sa.DateTime(), nullable=True),
            sa.Column("last_synced_at", sa.DateTime(), nullable=True),
            sa.Column("sync_hash", sa.String(length=64), nullable=True),
            sa.ForeignKeyConstraint(["duplicate_of_id"], ["camp.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("slug"),
            sa.UniqueConstraint("source_system", "external_id", name="uq_camp_source_external"),
        )
        op.create_index("ix_camp_source_system", "camp", ["source_system"])
        op.create_index("ix_camp_external_id", "camp", ["external_id"])
        op.create_index("ix_camp_slug", "camp", ["slug"])
        op.create_index("ix_camp_sport", "camp", ["sport"])
        op.create_index("ix_camp_level", "camp", ["level"])
        op.create_index("ix_camp_country", "camp", ["country"])
        op.create_index("ix_camp_city", "camp", ["city"])
        op.create_index("ix_camp_start_date", "camp", ["start_date"])
        op.create_index("ix_camp_end_date", "camp", ["end_date"])
        op.create_index("ix_camp_price_from", "camp", ["price_from"])
        op.create_index("ix_camp_publication_status", "camp", ["publication_status"])
        op.create_index("ix_camp_availability_status", "camp", ["availability_status"])
        op.create_index("ix_camp_priority", "camp", ["priority"])
        op.create_index("ix_camp_is_featured", "camp", ["is_featured"])
        op.create_index("ix_camp_is_owner_camp", "camp", ["is_owner_camp"])
        op.create_index("ix_camp_sync_hash", "camp", ["sync_hash"])
        op.create_index(
            "ix_camp_dup_probe",
            "camp",
            ["title", "country", "start_date", "organizer_name", "sport"],
        )

    tables = table_names(conn)
    if "camp_import_log" not in tables:
        op.create_table(
            "camp_import_log",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("source_system", sa.String(length=32), nullable=False),
            sa.Column("fetched_count", sa.Integer(), nullable=False),
            sa.Column("created_count", sa.Integer(), nullable=False),
            sa.Column("updated_count", sa.Integer(), nullable=False),
            sa.Column("skipped_count", sa.Integer(), nullable=False),
            sa.Column("duplicate_count", sa.Integer(), nullable=False),
            sa.Column("archived_count", sa.Integer(), nullable=False),
            sa.Column("error_count", sa.Integer(), nullable=False),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("details_json", sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    tables = table_names(conn)
    if "camp_lead" not in tables:
        op.create_table(
            "camp_lead",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("camp_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("phone", sa.String(length=64), nullable=True),
            sa.Column("telegram", sa.String(length=128), nullable=True),
            sa.Column("level", sa.String(length=64), nullable=True),
            sa.Column("comment", sa.Text(), nullable=True),
            sa.Column("source", sa.String(length=64), nullable=False),
            sa.Column("notification_status", sa.String(length=32), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["camp_id"], ["camp.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_camp_lead_camp_id", "camp_lead", ["camp_id"])


def downgrade():
    op.drop_table("camp_lead")
    op.drop_table("camp_import_log")
    op.drop_table("camp")
