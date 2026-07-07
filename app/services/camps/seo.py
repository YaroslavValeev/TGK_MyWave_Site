"""SEO helpers for Camp pages."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from flask import url_for

from app.database.camp_models import Camp
from app.services.camps.public import get_effective_camp


def _public_base_url() -> str:
    try:
        from flask import current_app
        base = (current_app.config.get("SERVER_NAME") or "").strip()
        if base and not base.startswith("http"):
            return f"https://{base}"
        if base:
            return base.rstrip("/")
    except RuntimeError:
        pass
    return "https://mywavetreaning.ru"


def camp_canonical_url(slug: str) -> str:
    return f"{_public_base_url()}/projects/camp/{slug}"


def build_camp_seo(camp: Camp) -> Dict[str, Any]:
    eff = get_effective_camp(camp)
    title = eff.get("seo_title") or eff.get("title") or "Camp"
    description = eff.get("seo_description") or eff.get("short_description") or ""
    h1 = eff.get("seo_h1") or eff.get("title") or title
    canonical = eff.get("canonical_url") or camp_canonical_url(camp.slug)
    robots = "index,follow" if camp.publication_status == "published" and eff.get("robots_index", True) else "noindex,nofollow"
    return {
        "title": f"{title} — MyWave Camp",
        "meta_description": (description or "")[:320],
        "h1": h1,
        "canonical_url": canonical,
        "robots": robots,
    }


def build_camp_json_ld(camp: Camp) -> Dict[str, Any]:
    eff = get_effective_camp(camp)
    start = eff.get("start_date")
    end = eff.get("end_date")
    location_name = eff.get("location_name") or eff.get("city") or eff.get("country")
    event: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": eff.get("title"),
        "description": eff.get("short_description") or eff.get("description"),
        "startDate": start,
        "endDate": end or start,
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "eventStatus": "https://schema.org/EventScheduled",
        "image": eff.get("cover_image_url"),
        "url": eff.get("canonical_url") or camp_canonical_url(camp.slug),
        "organizer": {
            "@type": "Organization",
            "name": eff.get("organizer_name") or "MyWave",
        },
    }
    if location_name:
        place: Dict[str, Any] = {
            "@type": "Place",
            "name": location_name,
            "address": eff.get("address") or location_name,
        }
        if eff.get("lat") and eff.get("lng"):
            place["geo"] = {"@type": "GeoCoordinates", "latitude": eff["lat"], "longitude": eff["lng"]}
        event["location"] = place
    if eff.get("price_from"):
        event["offers"] = {
            "@type": "Offer",
            "price": eff["price_from"],
            "priceCurrency": eff.get("currency") or "RUB",
            "url": eff.get("booking_url") or event["url"],
            "availability": "https://schema.org/InStock",
        }
    return event


def camp_json_ld_script(camp: Camp) -> str:
    return json.dumps(build_camp_json_ld(camp), ensure_ascii=False)
