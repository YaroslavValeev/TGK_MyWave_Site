"""Normalized read-model for events/competitions content (Events-1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Mapping, Optional

from app.services.events.content_types import ContentType, EventTrackStatus


def _norm_key_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    return {str(k).strip().lower(): v for k, v in row.items() if k is not None}


def _pick_str(row: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        val = row.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return ""


@dataclass(slots=True)
class ClassificationResult:
    content_type: ContentType
    track_status: EventTrackStatus
    confidence: float
    needs_review: bool
    reasons: List[str] = field(default_factory=list)
    source_hint: str = "raw_feed"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "content_type": self.content_type,
            "track_status": self.track_status,
            "confidence": round(self.confidence, 3),
            "needs_review": self.needs_review,
            "reasons": list(self.reasons),
            "source_hint": self.source_hint,
        }


@dataclass(slots=True)
class NormalizedContentItem:
    """
    Unified DTO for event-like content (not wired to public UI in Events-1).
    """

    event_id: str
    source_id: str
    source_type: str
    source_url: str
    content_type: ContentType
    title: str
    short_description: str
    sport_type: str
    start_date: Optional[date]
    end_date: Optional[date]
    start_time: str
    location_name: str
    location_url: str
    city: str
    organizer_name: str
    registration_url: str
    price_label: str
    track_status: EventTrackStatus
    media_status: str
    cover_image_path: str
    source_media_url: str
    created_at: str
    updated_at: str
    classification: ClassificationResult

    def as_public_safe_dict(self) -> Dict[str, Any]:
        """No full_description; safe for future API diagnostics."""
        return {
            "event_id": self.event_id,
            "content_type": self.content_type,
            "title": self.title,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "city": self.city or None,
            "track_status": self.track_status,
            "needs_review": self.classification.needs_review,
        }


def normalize_competitions_ticker_row(
    row: Mapping[str, Any],
    classification: ClassificationResult,
    *,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> NormalizedContentItem:
    r = _norm_key_row(row)
    event_id = _pick_str(r, "id") or _pick_str(r, "event_id")
    title = _pick_str(r, "event_name", "title", "raw_title")
    return NormalizedContentItem(
        event_id=event_id,
        source_id=event_id,
        source_type=_pick_str(r, "source_name") or "competitions_ticker",
        source_url=_pick_str(r, "source_url", "event_url"),
        content_type="competition",
        title=title,
        short_description=_pick_str(r, "ticker_text"),
        sport_type=_pick_str(r, "discipline"),
        start_date=start_date,
        end_date=end_date,
        start_time="",
        location_name=_pick_str(r, "location"),
        location_url="",
        city=_pick_str(r, "location"),
        organizer_name=_pick_str(r, "source_name"),
        registration_url=_pick_str(r, "event_url"),
        price_label="",
        track_status=classification.track_status,
        media_status="",
        cover_image_path="",
        source_media_url="",
        created_at=_pick_str(r, "created_at", "updated_at"),
        updated_at=_pick_str(r, "updated_at"),
        classification=classification,
    )


def normalize_raw_feed_row(
    row: Mapping[str, Any],
    classification: ClassificationResult,
    *,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> NormalizedContentItem:
    r = _norm_key_row(row)
    event_id = _pick_str(r, "id", "news_id", "raw_id", "slug")
    title = _pick_str(r, "title", "raw_title")
    excerpt = _pick_str(r, "summary", "excerpt", "lead")
    return NormalizedContentItem(
        event_id=event_id,
        source_id=event_id,
        source_type=_pick_str(r, "source_type") or "raw_feed",
        source_url=_pick_str(r, "source_url", "canonical_url"),
        content_type=classification.content_type,
        title=title,
        short_description=excerpt,
        sport_type=_pick_str(r, "sport_type", "discipline"),
        start_date=start_date,
        end_date=end_date,
        start_time=_pick_str(r, "start_time"),
        location_name=_pick_str(r, "location_name", "location"),
        location_url=_pick_str(r, "location_url"),
        city=_pick_str(r, "city"),
        organizer_name=_pick_str(r, "organizer_name", "organizer", "source_name"),
        registration_url=_pick_str(r, "registration_url"),
        price_label=_pick_str(r, "price_label", "price"),
        track_status=classification.track_status,
        media_status=_pick_str(r, "media_status"),
        cover_image_path="",
        source_media_url=_pick_str(r, "cover_image_url", "image_url"),
        created_at=_pick_str(r, "created_at"),
        updated_at=_pick_str(r, "updated_at", "published_at"),
        classification=classification,
    )
