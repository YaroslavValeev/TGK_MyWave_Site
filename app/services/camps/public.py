"""Effective camp view: merge source fields with site_overrides."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

from app.database.camp_models import Camp
from app.services.camps.schema import SITE_OVERRIDE_FIELDS, SOURCE_BADGE_LABELS


def get_effective_camp(camp: Camp) -> Dict[str, Any]:
    data = {
        "id": camp.id,
        "slug": camp.slug,
        "source_system": camp.source_system,
        "external_id": camp.external_id,
        "source_url": camp.source_url,
        "title": camp.title,
        "short_description": camp.short_description,
        "description": camp.description,
        "sport": camp.sport,
        "level": camp.level,
        "country": camp.country,
        "region": camp.region,
        "city": camp.city,
        "location_name": camp.location_name,
        "address": camp.address,
        "lat": camp.lat,
        "lng": camp.lng,
        "start_date": camp.start_date.isoformat() if camp.start_date else None,
        "end_date": camp.end_date.isoformat() if camp.end_date else None,
        "duration_days": camp.duration_days,
        "price_from": camp.price_from,
        "price_to": camp.price_to,
        "currency": camp.currency,
        "price_note": camp.price_note,
        "included": camp.included,
        "not_included": camp.not_included,
        "organizer_name": camp.organizer_name,
        "organizer_type": camp.organizer_type,
        "booking_url": camp.booking_url,
        "lead_form_enabled": camp.lead_form_enabled,
        "cover_image_url": camp.cover_image_url,
        "gallery": camp.gallery or [],
        "video_url": camp.video_url,
        "publication_status": camp.publication_status,
        "availability_status": camp.availability_status,
        "priority": camp.priority,
        "is_featured": camp.is_featured,
        "is_owner_camp": camp.is_owner_camp,
        "seo_title": camp.seo_title,
        "seo_description": camp.seo_description,
        "seo_h1": camp.seo_h1,
        "canonical_url": camp.canonical_url,
        "robots_index": camp.robots_index,
        "why_recommend": None,
        "source_badge": _source_badge(camp),
        "is_archived": camp.publication_status == "archived",
    }
    overrides = camp.site_overrides or {}
    for key in SITE_OVERRIDE_FIELDS:
        if key in overrides and overrides[key] is not None:
            data[key] = overrides[key]
    return data


def _source_badge(camp: Camp) -> str:
    if camp.is_owner_camp or camp.source_system in ("owner", "manual"):
        return SOURCE_BADGE_LABELS["owner"]
    if camp.organizer_type == "partner" or camp.source_system == "partner":
        return SOURCE_BADGE_LABELS["partner"]
    if camp.source_system == "mywavetour":
        return SOURCE_BADGE_LABELS["mywavetour"]
    return SOURCE_BADGE_LABELS.get(camp.source_system, camp.source_system)


def camp_to_api_dict(camp: Camp) -> Dict[str, Any]:
    return deepcopy(get_effective_camp(camp))
