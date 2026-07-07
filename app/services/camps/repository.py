"""Camp repository: upsert, query, archive."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import or_

from app.database.camp_models import Camp
from app.services.camps.schema import SITE_OVERRIDE_FIELDS

# Fields preserved on sync update (admin/site decisions must not be overwritten).
SYNC_SKIP_ON_UPDATE = frozenset({
    "publication_status",
    "duplicate_of_id",
    "robots_index",
    "is_featured",
    "priority",
    "canonical_url",
    "seo_title",
    "seo_description",
    "seo_h1",
})


def _apply_dict(model: Camp, data: Dict[str, Any], *, skip: frozenset[str] = frozenset()) -> None:
    for key, value in data.items():
        if key in skip or key == "site_overrides" or key == "normalized_title_key":
            continue
        if key in SITE_OVERRIDE_FIELDS and getattr(model, key, None) not in (None, "", [], {}):
            continue
        if hasattr(model, key):
            setattr(model, key, value)


def upsert_camp(session, camp: Dict[str, Any], existing: Optional[Camp] = None) -> Camp:
    """Insert or update camp; preserve publication_status and site_overrides on sync."""
    if existing is None:
        existing = Camp()
        session.add(existing)
        camp.setdefault("publication_status", "pending_review")
        if camp.get("source_system") == "mywavetour":
            camp.setdefault("robots_index", False)
        _apply_dict(existing, camp)
    else:
        overrides = dict(existing.site_overrides or {})
        _apply_dict(existing, camp, skip=SYNC_SKIP_ON_UPDATE)
        existing.site_overrides = overrides or existing.site_overrides

    existing.last_synced_at = datetime.utcnow()
    return existing


def archive_expired_camps(session, today: Optional[date] = None) -> int:
    today = today or date.today()
    rows = (
        session.query(Camp)
        .filter(
            Camp.end_date.isnot(None),
            Camp.end_date < today,
            Camp.publication_status.in_(("published", "pending_review", "hidden", "possible_duplicate")),
        )
        .all()
    )
    count = 0
    for row in rows:
        row.publication_status = "archived"
        count += 1
    return count


def list_public_camps(session, filters: Optional[Dict[str, Any]] = None) -> List[Camp]:
    filters = filters or {}
    q = session.query(Camp).filter(Camp.publication_status == "published")
    if filters.get("sport"):
        q = q.filter(Camp.sport == filters["sport"])
    if filters.get("level"):
        q = q.filter(Camp.level == filters["level"])
    if filters.get("country"):
        q = q.filter(Camp.country == filters["country"])
    if filters.get("availability"):
        q = q.filter(Camp.availability_status == filters["availability"])
    if filters.get("price_max"):
        q = q.filter(or_(Camp.price_from.is_(None), Camp.price_from <= int(filters["price_max"])))
    if filters.get("month"):
        ym = str(filters["month"])
        if len(ym) >= 7:
            y, m = int(ym[:4]), int(ym[5:7])
            from calendar import monthrange

            start = date(y, m, 1)
            end = date(y, m, monthrange(y, m)[1])
            q = q.filter(Camp.start_date <= end, or_(Camp.end_date.is_(None), Camp.end_date >= start))
    q = q.order_by(Camp.is_featured.desc(), Camp.priority.desc(), Camp.start_date.asc())
    return q.all()


def get_camp_by_slug(session, slug: str) -> Optional[Camp]:
    return session.query(Camp).filter(Camp.slug == slug).one_or_none()


def get_similar_camps(session, camp: Camp, limit: int = 4) -> List[Camp]:
    q = (
        session.query(Camp)
        .filter(Camp.publication_status == "published", Camp.id != camp.id)
        .filter(or_(Camp.sport == camp.sport, Camp.country == camp.country))
        .order_by(Camp.is_featured.desc(), Camp.start_date.asc())
        .limit(limit)
    )
    return q.all()
