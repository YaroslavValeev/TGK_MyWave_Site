"""In-memory events store with filters (Events-2)."""

from __future__ import annotations

import time
from datetime import date
from typing import Any, Callable, Dict, List, Optional

from flask import current_app

from app.modules.logger import get_logger
from app.services.competitions.visibility import parse_iso_date
from app.services.events.content_types import CONTENT_TYPES, EVENT_TRACK_STATUSES
from app.services.events.loader import load_classified_items
from app.services.events.review_queue import build_review_queue
from app.services.events.schema import NormalizedContentItem

logger = get_logger(__name__)

_cache: Dict[str, Any] = {"items": [], "ts": 0.0, "source": "all"}


def invalidate_events_cache() -> None:
    _cache["items"] = []
    _cache["ts"] = 0.0


def _cache_ttl_seconds() -> int:
    try:
        ttl = int(current_app.config.get("EVENTS_SHEETS_CACHE_TTL", 300))
    except RuntimeError:
        ttl = 300
    return max(0, ttl)


def _load_items(
    source: str = "all",
    *,
    loader: Optional[Callable[..., List[NormalizedContentItem]]] = None,
) -> List[NormalizedContentItem]:
    ttl = _cache_ttl_seconds()
    now = time.time()
    if (
        ttl > 0
        and _cache.get("items")
        and _cache.get("source") == source
        and (now - _cache.get("ts", 0)) < ttl
    ):
        return list(_cache["items"])

    try:
        if loader is not None:
            items = loader(source=source)
        else:
            items = load_classified_items(source=source)
        _cache["items"] = items
        _cache["ts"] = now
        _cache["source"] = source
        return list(items)
    except Exception as exc:
        logger.warning("events_store_load_failed source=%s err=%s", source, exc)
        if _cache.get("items") and _cache.get("source") == source:
            return list(_cache["items"])
        return []


def _city_matches(item: NormalizedContentItem, city: str) -> bool:
    needle = city.strip().lower()
    if not needle:
        return True
    hay = " ".join(
        p
        for p in (item.city, item.location_name)
        if p
    ).lower()
    return needle in hay


def _date_in_range(
    item: NormalizedContentItem,
    from_date: Optional[date],
    to_date: Optional[date],
) -> bool:
    if not item.start_date:
        return from_date is None and to_date is None
    if from_date and item.start_date < from_date:
        return False
    if to_date and item.start_date > to_date:
        return False
    return True


def list_items(
    *,
    content_type: Optional[str] = None,
    track_status: Optional[str] = None,
    city: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    source: str = "all",
    loader: Optional[Callable[..., List[NormalizedContentItem]]] = None,
) -> Dict[str, Any]:
    items = _load_items(source, loader=loader)

    ct = (content_type or "").strip().lower()
    ts = (track_status or "").strip().lower()
    fd = parse_iso_date(from_date) if from_date else None
    td = parse_iso_date(to_date) if to_date else None

    filtered: List[NormalizedContentItem] = []
    for item in items:
        if ct and item.content_type != ct:
            continue
        if ts and item.track_status != ts:
            continue
        if not _city_matches(item, city or ""):
            continue
        if not _date_in_range(item, fd, td):
            continue
        filtered.append(item)

    limit = max(1, min(int(limit or 50), 100))
    offset = max(0, int(offset or 0))
    page = filtered[offset : offset + limit]

    return {
        "items": page,
        "count": len(page),
        "total": len(filtered),
        "filters_applied": {
            k: v
            for k, v in {
                "content_type": ct or None,
                "track_status": ts or None,
                "city": (city or "").strip() or None,
                "from_date": from_date,
                "to_date": to_date,
                "source": source,
                "limit": limit,
                "offset": offset,
            }.items()
            if v is not None
        },
    }


def list_review_queue(
    *,
    limit: int = 50,
    offset: int = 0,
    source: str = "all",
    loader: Optional[Callable[..., List[NormalizedContentItem]]] = None,
) -> Dict[str, Any]:
    items = _load_items(source, loader=loader)
    queue = build_review_queue(items)
    limit = max(1, min(int(limit or 50), 100))
    offset = max(0, int(offset or 0))
    page = queue[offset : offset + limit]
    return {
        "items": page,
        "count": len(page),
        "total": len(queue),
        "filters_applied": {
            "track_status": "needs_review",
            "source": source,
            "limit": limit,
            "offset": offset,
        },
    }


def get_diagnostics(
    *,
    source: str = "all",
    loader: Optional[Callable[..., List[NormalizedContentItem]]] = None,
) -> Dict[str, Any]:
    items = _load_items(source, loader=loader)
    by_content_type: Dict[str, int] = {k: 0 for k in sorted(CONTENT_TYPES)}
    by_track_status: Dict[str, int] = {k: 0 for k in sorted(EVENT_TRACK_STATUSES)}

    for item in items:
        by_content_type[item.content_type] = by_content_type.get(item.content_type, 0) + 1
        by_track_status[item.track_status] = by_track_status.get(item.track_status, 0) + 1

    needs_review_count = sum(1 for it in items if it.classification.needs_review)
    ttl = _cache_ttl_seconds()
    cache_age = int(time.time() - _cache.get("ts", 0)) if _cache.get("ts") else None

    spreadsheet_tail = None
    sheet_name = None
    try:
        from app.services.parser_news_sheet import resolve_parser_source

        sid, wst = resolve_parser_source()
        spreadsheet_tail = (sid or "")[-8:] if sid else None
        sheet_name = wst
    except Exception:
        pass

    return {
        "total_items": len(items),
        "needs_review_count": needs_review_count,
        "by_content_type": by_content_type,
        "by_track_status": by_track_status,
        "cache_age_seconds": cache_age,
        "cache_ttl_seconds": ttl,
        "spreadsheet_id_tail": spreadsheet_tail,
        "sheet_name": sheet_name,
        "source": source,
    }
