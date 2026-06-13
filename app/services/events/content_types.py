"""Canonical content_type and event-track status values (Events-1)."""

from __future__ import annotations

from typing import Literal

ContentType = Literal["event", "competition", "camp", "workshop", "news"]
EventTrackStatus = Literal["draft", "parsed", "needs_review", "published", "archived"]

CONTENT_TYPES: frozenset[str] = frozenset(
    {"event", "competition", "camp", "workshop", "news"}
)

EVENT_TRACK_STATUSES: frozenset[str] = frozenset(
    {"draft", "parsed", "needs_review", "published", "archived"}
)

NEEDS_REVIEW_STATUS: EventTrackStatus = "needs_review"

# Minimum classifier confidence to avoid needs_review (0..1).
CLASSIFIER_CONFIDENCE_THRESHOLD = 0.55
