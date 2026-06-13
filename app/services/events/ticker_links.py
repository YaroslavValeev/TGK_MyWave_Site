"""Home competitions ticker link enrichment (Events-3)."""

from __future__ import annotations

from typing import Any, Dict, List

from app.config.events_features import is_events_api_enabled, is_events_public_ui_flag_set
from app.services.events.public_urls import public_detail_path
from app.services.events.store import get_public_items
from app.services.events.slug import find_public_item_by_event_id


def enrich_competitions_ticker(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    When public UI is active, link ticker rows to /events/<slug> if detail exists.
    Otherwise preserve existing href (external URL) or plain text.
    """
    if not is_events_public_ui_flag_set() or not is_events_api_enabled():
        return items
    if not items:
        return items

    try:
        public_items = get_public_items()
    except Exception:
        return items

    enriched: List[Dict[str, Any]] = []
    for row in items:
        copy = dict(row)
        copy.setdefault("href_external", True)
        event_id = str(copy.get("id") or "").strip()
        matched = find_public_item_by_event_id(event_id, public_items) if event_id else None
        if matched:
            path = public_detail_path(matched)
            if path:
                copy["href"] = path
                copy["href_external"] = False
        enriched.append(copy)
    return enriched
