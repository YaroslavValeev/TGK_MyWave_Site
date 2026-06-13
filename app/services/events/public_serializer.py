"""SSR-safe serialization for Events-3 public pages."""

from __future__ import annotations

from typing import Any, Dict, List, Set

from app.services.events.public_urls import get_public_site_base_url, public_detail_path
from app.services.events.schema import NormalizedContentItem

_FORBIDDEN_PUBLIC_KEYS: Set[str] = frozenset(
    {
        "source_url",
        "registration_url",
        "location_url",
        "source_media_url",
        "raw_content",
        "raw_html",
        "final_posts",
        "text",
        "parent_name",
        "parent_phone",
        "health_notes",
        "organizer_name",
        "source_id",
    }
)

_MAX_SUMMARY = 320


def _date_range(item: NormalizedContentItem) -> str:
    if item.start_date and item.end_date and item.end_date != item.start_date:
        return f"{item.start_date.isoformat()} — {item.end_date.isoformat()}"
    if item.start_date:
        return item.start_date.isoformat()
    return ""


def serialize_public_card(item: NormalizedContentItem) -> Dict[str, Any]:
    summary = (item.short_description or "")[:_MAX_SUMMARY]
    detail_path = public_detail_path(item)
    payload = {
        "event_id": item.event_id,
        "name": item.title,
        "summary": summary,
        "date_range": _date_range(item),
        "city": item.city or item.location_name or "",
        "content_type": item.content_type,
        "cover": None,
        "cta_url": detail_path,
        "url": detail_path,
        "sport_type": item.sport_type or None,
    }
    for key in _FORBIDDEN_PUBLIC_KEYS:
        payload.pop(key, None)
    return payload


def serialize_public_detail(item: NormalizedContentItem) -> Dict[str, Any]:
    card = serialize_public_card(item)
    card["description"] = (item.short_description or "")[:800]
    card["location_name"] = item.location_name or item.city or ""
    card["slug"] = public_detail_path(item).rsplit("/", 1)[-1] if public_detail_path(item) else ""
    return card


def build_public_json_ld_item(item: NormalizedContentItem) -> Dict[str, Any]:
    base = get_public_site_base_url()
    path = public_detail_path(item)
    location_name = item.location_name or item.city or "TBD"
    payload: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": item.title,
        "startDate": item.start_date.isoformat() if item.start_date else None,
        "location": {
            "@type": "Place",
            "name": location_name,
            "address": location_name,
        },
        "description": (item.short_description or item.title or "")[:500],
        "eventStatus": "https://schema.org/EventScheduled",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "url": f"{base}{path}" if path else f"{base}/events",
    }
    if item.end_date:
        payload["endDate"] = item.end_date.isoformat()
    return payload


def build_public_json_ld_list(items: List[NormalizedContentItem]) -> List[Dict[str, Any]]:
    return [build_public_json_ld_item(it) for it in items if it.start_date]


def assert_public_payload_safe(payload: Dict[str, Any]) -> None:
    leaked = _FORBIDDEN_PUBLIC_KEYS.intersection(payload.keys())
    if leaked:
        raise AssertionError(f"unsafe_public_keys:{sorted(leaked)}")
