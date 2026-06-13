"""Public-safe API serialization for events (Events-2)."""

from __future__ import annotations

from typing import Any, Dict, Set

from app.services.events.schema import NormalizedContentItem

# Fields never exposed via Events-2 read-only API.
_FORBIDDEN_API_KEYS: Set[str] = frozenset(
    {
        "source_url",
        "registration_url",
        "location_url",
        "source_media_url",
        "cover_image_path",
        "short_description",
        "full_description",
        "raw_content",
        "raw_html",
        "final_posts",
        "text",
        "parent_name",
        "parent_phone",
        "health_notes",
        "organizer_name",
        "source_id",
        "created_at",
        "updated_at",
    }
)


def serialize_api_item(item: NormalizedContentItem) -> Dict[str, Any]:
    """Allowlisted public fields only — no raw body, URLs, or PII-like columns."""
    payload = {
        "event_id": item.event_id,
        "content_type": item.content_type,
        "title": (item.title or "")[:280],
        "start_date": item.start_date.isoformat() if item.start_date else None,
        "end_date": item.end_date.isoformat() if item.end_date else None,
        "city": item.city or None,
        "location_name": item.location_name or None,
        "sport_type": item.sport_type or None,
        "track_status": item.track_status,
        "needs_review": item.classification.needs_review,
        "confidence": round(item.classification.confidence, 3),
        "source_hint": item.classification.source_hint,
    }
    for key in _FORBIDDEN_API_KEYS:
        payload.pop(key, None)
    return payload


def assert_api_payload_safe(payload: Dict[str, Any]) -> None:
    """Test helper: ensure serializer did not leak forbidden keys."""
    leaked = _FORBIDDEN_API_KEYS.intersection(payload.keys())
    if leaked:
        raise AssertionError(f"unsafe_api_keys:{sorted(leaked)}")
