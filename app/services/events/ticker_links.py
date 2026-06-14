"""Home competitions ticker link enrichment (Events-3)."""

from __future__ import annotations

from typing import Any, Dict, List

from app.config.events_features import is_events_api_enabled, is_events_public_ui_flag_set
from app.services.events.public_urls import public_detail_path
from app.services.events.store import get_public_items
from app.services.events.slug import find_public_item_by_event_id


def enrich_competitions_ticker(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    When public UI is active, keep external source href when present.
    Fall back to /events/<slug> only when no source URL exists.
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
        existing_href = (copy.get("href") or "").strip()
        event_id = str(copy.get("id") or "").strip()
        matched = find_public_item_by_event_id(event_id, public_items) if event_id else None

        if existing_href:
            # Источник из Sheets (source_url / event_url) — приоритет для ticker.
            copy["href"] = existing_href
            copy["href_external"] = existing_href.startswith(("http://", "https://", "//"))
        elif matched:
            path = public_detail_path(matched)
            if path:
                copy["href"] = path
                copy["href_external"] = False
        else:
            copy.setdefault("href_external", bool(copy.get("href")))

        enriched.append(copy)
    return enriched
