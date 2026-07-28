"""Seasonal gym schedule and booking provider config."""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import List, Set, Tuple

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _flag(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in _TRUTHY


def is_seasonal_rules_enabled() -> bool:
    return _flag("BOOKING_SEASONAL_RULES_ENABLED", "0")


def seasonal_rules_until() -> date:
    raw = os.environ.get("BOOKING_SEASONAL_RULES_UNTIL", "2026-09-30").strip()
    return date.fromisoformat(raw)


def gym_seasonal_weekdays() -> Set[int]:
    """Monday=0 .. Sunday=6."""
    raw = os.environ.get("GYM_SEASONAL_WEEKDAYS", "0,3").strip()
    out: Set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            wd = int(part)
        except ValueError:
            continue
        if 0 <= wd <= 6:
            out.add(wd)
    return out or {0, 3}


def gym_seasonal_start_time() -> str:
    return os.environ.get("GYM_SEASONAL_START_TIME", "19:00").strip() or "19:00"


def gym_seasonal_duration_minutes() -> int:
    try:
        return max(1, int(os.environ.get("GYM_SEASONAL_DURATION_MINUTES", "90")))
    except (TypeError, ValueError):
        return 90


def gym_capacity() -> int:
    try:
        return max(1, int(os.environ.get("GYM_CAPACITY", "4")))
    except (TypeError, ValueError):
        return 4


def boat_provider() -> str:
    return os.environ.get("BOAT_PROVIDER", "yclients").strip().lower() or "yclients"


def boat_slot_duration_minutes() -> int:
    """Календарный слот / шаг сетки: 30 мин = 25 катание + 5 тех. (пирс)."""
    try:
        return max(1, int(os.environ.get("BOAT_SLOT_DURATION_MINUTES", "30")))
    except (TypeError, ValueError):
        return 30


def boat_seance_minutes() -> int:
    """Чистое катание в YCLIENTS seance_length (минуты). Default 25."""
    try:
        return max(1, int(os.environ.get("BOAT_SEANCE_MINUTES", "25")))
    except (TypeError, ValueError):
        return 25


def boat_capacity() -> int:
    try:
        return max(1, int(os.environ.get("BOAT_CAPACITY", "1")))
    except (TypeError, ValueError):
        return 1


def is_operational_summary_enabled() -> bool:
    return _flag("BOOKING_OPERATIONAL_SUMMARY_ENABLED", "0")


def yclients_widget_url() -> str:
    return os.environ.get(
        "YCLIENTS_WIDGET_URL",
        "https://n347190.yclients.com/company/2043174/personal/menu?o=",
    ).strip()


def parse_booking_date(date_str: str) -> date:
    return date.fromisoformat(str(date_str).strip()[:10])


def normalize_time_hhmm(time_str: str) -> str:
    raw = str(time_str or "").strip()
    if len(raw) >= 5 and raw[2] == ":":
        h, m = raw[:5].split(":")
        return f"{int(h):02d}:{int(m):02d}"
    return raw
