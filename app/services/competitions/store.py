"""
Чтение листа competitions_ticker из Parser News + in-memory cache.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from flask import current_app

from app.modules.logger import get_logger
from app.services.competitions.sheet import resolve_competitions_source
from app.services.competitions.visibility import (
    build_ticker_text,
    is_ticker_live_row,
    is_ticker_visible_row,
    resolve_ticker_href,
    sort_key_for_ticker,
)
from app.services.google import read_sheet

logger = get_logger(__name__)

_cache: Dict[str, Dict] = {"sheets_data": {"ts": 0, "data": []}}


def invalidate_competitions_sheets_cache() -> None:
    _cache["sheets_data"] = {"ts": 0, "data": []}


def _cache_ttl_seconds() -> int:
    try:
        ttl = int(current_app.config.get("COMPETITIONS_SHEETS_CACHE_TTL", 300))
    except RuntimeError:
        ttl = 300
    return max(0, ttl)


def _normalize_row(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {str(k).strip().lower(): v for k, v in raw.items() if k is not None}


def _row_to_ticker_item(row: Dict[str, Any]) -> Dict[str, Any]:
    href = resolve_ticker_href(row)
    return {
        "id": str(row.get("id") or "").strip(),
        "label": build_ticker_text(row),
        "href": href,
        "href_external": bool(href),
        "is_live": is_ticker_live_row(row),
        "discipline": str(row.get("discipline") or "").strip().lower(),
        "event_name": str(row.get("event_name") or "").strip(),
        "start_date": str(row.get("start_date") or "").strip()[:10],
        "end_date": str(row.get("end_date") or row.get("start_date") or "").strip()[:10],
        "source_name": str(row.get("source_name") or "").strip(),
    }


def _load_from_sheets() -> List[Dict[str, Any]]:
    spreadsheet_id, worksheet_title = resolve_competitions_source()
    tail = (spreadsheet_id or "")[-8:] if spreadsheet_id else None
    logger.info(
        "competitions_ticker_load",
        extra={
            "spreadsheet_id_tail": tail,
            "sheet_name": worksheet_title,
        },
    )
    records, _headers = read_sheet(spreadsheet_id, worksheet_title)
    visible_rows: List[Dict[str, Any]] = []
    for raw in records:
        row = _normalize_row(raw)
        if is_ticker_visible_row(row):
            visible_rows.append(row)
    visible_rows.sort(key=sort_key_for_ticker)
    items = [_row_to_ticker_item(row) for row in visible_rows]
    logger.info(
        "competitions_ticker_loaded",
        extra={
            "spreadsheet_id_tail": tail,
            "sheet_name": worksheet_title,
            "row_count": len(items),
        },
    )
    return items


def _load_cached() -> List[Dict[str, Any]]:
    ttl = _cache_ttl_seconds()
    now = time.time()
    entry = _cache["sheets_data"]
    if ttl > 0 and entry.get("data") and (now - entry.get("ts", 0)) < ttl:
        return entry["data"]

    try:
        data = _load_from_sheets()
        _cache["sheets_data"] = {"ts": now, "data": data}
        return data
    except Exception as e:
        logger.warning("competitions_ticker_load_failed: %s", e)
        if entry.get("data"):
            return entry["data"]
        return []


def get_ticker_items() -> List[Dict[str, Any]]:
    """Список элементов для бегущей строки на главной."""
    return _load_cached()
