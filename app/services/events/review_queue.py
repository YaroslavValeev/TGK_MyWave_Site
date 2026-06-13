"""Review queue helpers for classified events (Events-2)."""

from __future__ import annotations

from datetime import date
from typing import List

from app.services.events.schema import NormalizedContentItem


def build_review_queue(items: List[NormalizedContentItem]) -> List[NormalizedContentItem]:
    """
    Rows requiring editorial review, sorted by lowest confidence first.
    """
    queue = [item for item in items if item.classification.needs_review]
    queue.sort(
        key=lambda it: (
            it.classification.confidence,
            it.start_date or date.max,
            (it.title or "").lower(),
        )
    )
    return queue
