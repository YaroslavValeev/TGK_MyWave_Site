"""Load and classify rows from Parser News sheets (Events-2)."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from app.services.competitions.visibility import parse_iso_date
from app.services.events.classifier import (
    classify_competitions_ticker_row,
    classify_row,
)
from app.services.events.schema import (
    NormalizedContentItem,
    normalize_competitions_ticker_row,
    normalize_raw_feed_row,
)

RawFeedLoader = Callable[[], Tuple[List[Dict[str, Any]], List[str]]]
TickerLoader = Callable[[], Tuple[List[Dict[str, Any]], List[str]]]


def _parse_row_dates(row: Mapping[str, Any]) -> Tuple[Optional[Any], Optional[Any]]:
    r = {str(k).strip().lower(): v for k, v in row.items() if k is not None}
    start = parse_iso_date(
        r.get("start_date") or r.get("event_date") or r.get("date")
    )
    end = parse_iso_date(r.get("end_date")) or start
    return start, end


def load_from_raw_feed(
    records: Sequence[Mapping[str, Any]],
) -> List[NormalizedContentItem]:
    items: List[NormalizedContentItem] = []
    for raw in records:
        classification = classify_row(raw, source_hint="raw_feed")
        start, end = _parse_row_dates(raw)
        item = normalize_raw_feed_row(
            raw, classification, start_date=start, end_date=end
        )
        if item.event_id or item.title:
            items.append(item)
    return items


def load_from_competitions_ticker(
    records: Sequence[Mapping[str, Any]],
) -> List[NormalizedContentItem]:
    items: List[NormalizedContentItem] = []
    for raw in records:
        classification = classify_competitions_ticker_row(raw)
        start, end = _parse_row_dates(raw)
        item = normalize_competitions_ticker_row(
            raw, classification, start_date=start, end_date=end
        )
        if item.event_id or item.title:
            items.append(item)
    return items


def load_classified_items(
    *,
    source: str = "all",
    raw_feed_loader: Optional[RawFeedLoader] = None,
    ticker_loader: Optional[TickerLoader] = None,
) -> List[NormalizedContentItem]:
    """
    Load + classify items from configured sheets sources.
    Injectable loaders for unit tests (no Google calls).
    """
    source_norm = (source or "all").strip().lower()
    out: List[NormalizedContentItem] = []

    if source_norm in ("all", "raw_feed"):
        if raw_feed_loader is not None:
            records, _headers = raw_feed_loader()
        else:
            from app.services.parser_news_sheet import fetch_parser_news_rows

            records, _headers = fetch_parser_news_rows()
        out.extend(load_from_raw_feed(records))

    if source_norm in ("all", "competitions_ticker"):
        if ticker_loader is not None:
            records, _headers = ticker_loader()
        else:
            from app.services.competitions.sheet import resolve_competitions_source
            from app.services.google import read_sheet

            spreadsheet_id, worksheet = resolve_competitions_source()
            records, _headers = read_sheet(spreadsheet_id, worksheet)
        out.extend(load_from_competitions_ticker(records))

    return out
