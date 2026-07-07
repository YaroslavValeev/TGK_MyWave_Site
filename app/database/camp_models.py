"""ORM models for Projects / Camp catalog."""

from __future__ import annotations

from datetime import date, datetime

from app.database.models import db


class Camp(db.Model):
    __tablename__ = "camp"

    id = db.Column(db.Integer, primary_key=True)

    source_system = db.Column(db.String(32), nullable=False, index=True)
    external_id = db.Column(db.String(128), nullable=True, index=True)
    source_url = db.Column(db.Text, nullable=True)

    title = db.Column(db.String(320), nullable=False)
    slug = db.Column(db.String(320), unique=True, nullable=False, index=True)
    short_description = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)

    sport = db.Column(db.String(32), nullable=False, default="wakesurf", index=True)
    level = db.Column(db.String(32), nullable=False, default="all_levels", index=True)

    country = db.Column(db.String(128), nullable=True, index=True)
    region = db.Column(db.String(128), nullable=True)
    city = db.Column(db.String(128), nullable=True, index=True)
    location_name = db.Column(db.String(256), nullable=True)
    address = db.Column(db.Text, nullable=True)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)

    start_date = db.Column(db.Date, nullable=True, index=True)
    end_date = db.Column(db.Date, nullable=True, index=True)
    duration_days = db.Column(db.Integer, nullable=True)

    price_from = db.Column(db.Integer, nullable=True, index=True)
    price_to = db.Column(db.Integer, nullable=True)
    currency = db.Column(db.String(8), nullable=False, default="RUB")
    price_note = db.Column(db.Text, nullable=True)

    included = db.Column(db.Text, nullable=True)
    not_included = db.Column(db.Text, nullable=True)

    organizer_name = db.Column(db.String(256), nullable=True)
    organizer_type = db.Column(db.String(32), nullable=False, default="external")

    booking_url = db.Column(db.Text, nullable=True)
    lead_form_enabled = db.Column(db.Boolean, nullable=False, default=True)

    cover_image_url = db.Column(db.Text, nullable=True)
    gallery = db.Column(db.JSON, nullable=True)
    video_url = db.Column(db.Text, nullable=True)

    content_rights_status = db.Column(db.String(32), nullable=False, default="unknown")
    publication_status = db.Column(db.String(32), nullable=False, default="draft", index=True)
    availability_status = db.Column(db.String(32), nullable=False, default="unknown", index=True)

    priority = db.Column(db.Integer, nullable=False, default=0, index=True)
    is_featured = db.Column(db.Boolean, nullable=False, default=False, index=True)
    is_owner_camp = db.Column(db.Boolean, nullable=False, default=False, index=True)

    seo_title = db.Column(db.String(320), nullable=True)
    seo_description = db.Column(db.Text, nullable=True)
    seo_h1 = db.Column(db.String(320), nullable=True)
    canonical_url = db.Column(db.Text, nullable=True)
    robots_index = db.Column(db.Boolean, nullable=False, default=True)

    # Raw import payload + manual overrides (sync never overwrites non-null override keys).
    source_payload = db.Column(db.JSON, nullable=True)
    site_overrides = db.Column(db.JSON, nullable=True)
    duplicate_of_id = db.Column(db.Integer, db.ForeignKey("camp.id"), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    source_updated_at = db.Column(db.DateTime, nullable=True)
    last_synced_at = db.Column(db.DateTime, nullable=True)
    sync_hash = db.Column(db.String(64), nullable=True, index=True)

    duplicate_of = db.relationship("Camp", remote_side=[id], backref="duplicates")

    __table_args__ = (
        db.UniqueConstraint("source_system", "external_id", name="uq_camp_source_external"),
        db.Index("ix_camp_dup_probe", "title", "country", "start_date", "organizer_name", "sport"),
    )

    def is_published_public(self) -> bool:
        return self.publication_status == "published" and self.robots_index


class CampImportLog(db.Model):
    __tablename__ = "camp_import_log"

    id = db.Column(db.Integer, primary_key=True)
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(32), nullable=False, default="running")
    source_system = db.Column(db.String(32), nullable=False, default="mywavetour")
    fetched_count = db.Column(db.Integer, nullable=False, default=0)
    created_count = db.Column(db.Integer, nullable=False, default=0)
    updated_count = db.Column(db.Integer, nullable=False, default=0)
    skipped_count = db.Column(db.Integer, nullable=False, default=0)
    duplicate_count = db.Column(db.Integer, nullable=False, default=0)
    archived_count = db.Column(db.Integer, nullable=False, default=0)
    error_count = db.Column(db.Integer, nullable=False, default=0)
    message = db.Column(db.Text, nullable=True)
    details_json = db.Column(db.JSON, nullable=True)


class CampLead(db.Model):
    __tablename__ = "camp_lead"

    id = db.Column(db.Integer, primary_key=True)
    camp_id = db.Column(db.Integer, db.ForeignKey("camp.id"), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(64), nullable=True)
    telegram = db.Column(db.String(128), nullable=True)
    level = db.Column(db.String(64), nullable=True)
    comment = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(64), nullable=False, default="site_camp")
    notification_status = db.Column(db.String(32), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    camp = db.relationship("Camp", backref=db.backref("leads", lazy=True))
