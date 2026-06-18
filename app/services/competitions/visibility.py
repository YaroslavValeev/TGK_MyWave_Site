"""
Правила видимости строк competitions_ticker на главной (Contract v1).

Канон: docs/COMPETITIONS_TICKER_CONTRACT_v1.md
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Dict, Optional

ACTIVE_STATUS = "ACTIVE"

DISCIPLINE_LABELS = {
    "wakesurf": "Wakesurf",
    "wakeboard": "Wakeboard",
    "both": "Wakesurf / Wakeboard",
}


def _status_upper(status_raw: Optional[str]) -> str:
    return str(status_raw or "").strip().upper()


def parse_iso_date(value: Any) -> Optional[date]:
    """Парсит YYYY-MM-DD из ячейки Sheets."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    s = s[:10]
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def normalize_url(value: Any) -> Optional[str]:
    s = str(value or "").strip()
    if not s or s in ("-", "—", "n/a", "N/A"):
        return None
    if s.startswith("//"):
        s = "https:" + s
    if not s.startswith(("http://", "https://")):
        if "." in s and " " not in s:
            s = "https://" + s.lstrip("/")
        else:
            return None
    return s


def resolve_ticker_href(row: Dict[str, Any]) -> Optional[str]:
    # Для ticker ведём на первоисточник, если он есть; иначе на страницу события.
    for key in ("source_url", "event_url"):
        url = normalize_url(row.get(key))
        if url:
            return url
    return None


def _format_short_date(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def _format_date_range(start: date, end: date) -> str:
    if start == end:
        return _format_short_date(start)
    if start.year == end.year:
        return f"{start.strftime('%d.%m')}–{_format_short_date(end)}"
    return f"{_format_short_date(start)}–{_format_short_date(end)}"


def discipline_label(discipline_raw: Optional[str]) -> str:
    key = str(discipline_raw or "").strip().lower()
    return DISCIPLINE_LABELS.get(key, key.capitalize() if key else "Соревнование")


def build_ticker_text(row: Dict[str, Any]) -> str:
    custom = str(row.get("ticker_text") or "").strip()
    if custom:
        return custom

    name = str(row.get("event_name") or "").strip()
    location = str(row.get("location") or "").strip()
    country = str(row.get("country") or "").strip()
    place = ", ".join(p for p in (location, country) if p)

    start = parse_iso_date(row.get("start_date"))
    end = parse_iso_date(row.get("end_date")) or start
    dates_part = ""
    if start and end:
        dates_part = _format_date_range(start, end)

    parts = [discipline_label(row.get("discipline")), name]
    if place:
        parts.append(place)
    if dates_part:
        parts.append(dates_part)
    return " · ".join(p for p in parts if p)


def is_ticker_visible_row(row: Dict[str, Any], today: Optional[date] = None) -> bool:
    if today is None:
        today = datetime.now(timezone.utc).date()

    if _status_upper(row.get("status")) != ACTIVE_STATUS:
        return False

    if not str(row.get("event_name") or "").strip():
        return False

    start = parse_iso_date(row.get("start_date"))
    if not start:
        return False

    end = parse_iso_date(row.get("end_date")) or start
    if end < today:
        return False

    return True


def is_ticker_live_row(row: Dict[str, Any], today: Optional[date] = None) -> bool:
    """Событие идёт прямо сейчас (start <= today <= end)."""
    if today is None:
        today = datetime.now(timezone.utc).date()
    start = parse_iso_date(row.get("start_date"))
    if not start:
        return False
    end = parse_iso_date(row.get("end_date")) or start
    return start <= today <= end


def sort_key_for_ticker(row: Dict[str, Any]) -> tuple:
    start = parse_iso_date(row.get("start_date")) or date.max
    name = str(row.get("event_name") or "").strip().lower()
    return (start, name)
