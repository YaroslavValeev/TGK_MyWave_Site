"""Public eligibility gate for Events-3 vitrine."""

from __future__ import annotations

from app.services.events.schema import NormalizedContentItem

_EVENT_TYPES = frozenset({"competition", "event", "camp", "workshop"})


def is_public_eligible(item: NormalizedContentItem) -> bool:
    """
    Single gate for public list/detail. needs_review never appears publicly.
    """
    if item.classification.needs_review:
        return False
    if item.track_status == "needs_review":
        return False
    if item.track_status != "published":
        return False
    if not (item.title or "").strip():
        return False
    if item.content_type in _EVENT_TYPES and not item.start_date:
        return False
    return True
