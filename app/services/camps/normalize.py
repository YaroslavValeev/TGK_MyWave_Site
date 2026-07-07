"""Normalize raw MyWaveTour camp payload into Site camp dict."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from app.services.camps.schema import LEVELS, SPORTS


def _slugify(title: str, suffix: str = "") -> str:
    t = (title or "").strip().lower().replace("ё", "е")
    t = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in t)
    t = "-".join(p for p in t.split("-") if p) or "camp"
    if suffix:
        short = hashlib.md5(suffix.encode("utf-8")).hexdigest()[:6]
        return f"{t}-{short}"[:320]
    return t[:320]


def _parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    s = str(value).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _map_sport(raw: Any) -> str:
    s = str(raw or "").strip().lower()
    if s in SPORTS:
        return s
    if "вейксерф" in s or "wakesurf" in s:
        return "wakesurf"
    if "вейкборд" in s or "wakeboard" in s:
        return "wakeboard"
    if "mixed" in s or "оба" in s:
        return "mixed"
    return "wakesurf"


def _map_sports(raw: Any) -> str:
    if isinstance(raw, list):
        mapped = [_map_sport(item) for item in raw if item]
        if not mapped:
            return "wakesurf"
        unique = set(mapped)
        if len(unique) > 1:
            return "mixed"
        return mapped[0]
    return _map_sport(raw)


def _normalize_external_id(raw_id: Any) -> str:
    s = str(raw_id or "").strip()
    if not s:
        return ""
    if s.startswith("tour_") or s.startswith("tour-"):
        return s
    return f"tour_{s}"


def _map_level(raw: Any) -> str:
    s = str(raw or "").strip().lower()
    if s in LEVELS:
        return s
    mapping = {
        "нович": "beginner",
        "beginner": "beginner",
        "средн": "intermediate",
        "продвин": "advanced",
        "pro": "pro",
        "все": "all_levels",
    }
    for key, val in mapping.items():
        if key in s:
            return val
    return "all_levels"


def normalized_title_key(title: str) -> str:
    t = unicodedata.normalize("NFKC", (title or "").strip().lower())
    t = re.sub(r"\s+", " ", t)
    return t


def compute_sync_hash(payload: Dict[str, Any]) -> str:
    base = "|".join(
        str(payload.get(k) or "")
        for k in (
            "external_id",
            "title",
            "start_date",
            "end_date",
            "price_from",
            "country",
            "city",
            "sport",
            "availability_status",
        )
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def normalize_tour_camp(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Map MyWaveTour CampContract feed item → normalized camp dict (not yet persisted)."""
    external_id = _normalize_external_id(raw.get("id") or raw.get("external_id"))
    title = str(raw.get("title") or raw.get("name") or "").strip()
    start = _parse_date(raw.get("start_date") or raw.get("date_start"))
    end = _parse_date(raw.get("end_date") or raw.get("date_end"))
    sport = _map_sports(raw.get("sport") or raw.get("sports") or raw.get("discipline"))
    slug_base = _slugify(title or external_id or "camp")
    if start:
        slug_base = f"{slug_base}-{start.isoformat()}"

    price_from = raw.get("price_from") or raw.get("price") or raw.get("min_price")
    try:
        price_from = int(float(price_from)) if price_from not in (None, "") else None
    except (TypeError, ValueError):
        price_from = None

    price_to = raw.get("price_to") or raw.get("max_price")
    try:
        price_to = int(float(price_to)) if price_to not in (None, "") else None
    except (TypeError, ValueError):
        price_to = None

    gallery = raw.get("gallery") or raw.get("images")
    if isinstance(gallery, str):
        gallery = [u.strip() for u in gallery.split(",") if u.strip()]

    return {
        "source_system": "mywavetour",
        "external_id": external_id or None,
        "source_url": str(raw.get("url") or raw.get("source_url") or "").strip() or None,
        "title": title,
        "slug": slug_base[:320],
        "short_description": str(raw.get("short_description") or raw.get("summary") or "").strip() or None,
        "description": str(raw.get("description") or raw.get("content") or "").strip() or None,
        "sport": sport,
        "level": _map_level(raw.get("level")),
        "country": str(raw.get("country") or "").strip() or None,
        "region": str(raw.get("region") or "").strip() or None,
        "city": str(raw.get("city") or "").strip() or None,
        "location_name": str(raw.get("location_name") or raw.get("location") or "").strip() or None,
        "address": str(raw.get("address") or "").strip() or None,
        "lat": raw.get("lat") or raw.get("latitude"),
        "lng": raw.get("lng") or raw.get("longitude"),
        "start_date": start,
        "end_date": end,
        "duration_days": raw.get("duration_days"),
        "price_from": price_from,
        "price_to": price_to,
        "currency": str(raw.get("currency") or "RUB").strip()[:8],
        "price_note": str(raw.get("price_note") or "").strip() or None,
        "included": str(raw.get("included") or "").strip() or None,
        "not_included": str(raw.get("not_included") or "").strip() or None,
        "organizer_name": str(raw.get("organizer_name") or raw.get("organizer") or "").strip() or None,
        "organizer_type": "external",
        "booking_url": str(raw.get("booking_url") or raw.get("url") or "").strip() or None,
        "lead_form_enabled": bool(raw.get("lead_form_enabled", True)),
        "cover_image_url": str(raw.get("cover_image_url") or raw.get("image") or "").strip() or None,
        "gallery": gallery if isinstance(gallery, list) else None,
        "video_url": str(raw.get("video_url") or "").strip() or None,
        "content_rights_status": str(raw.get("content_rights_status") or "partner_allowed").strip(),
        "availability_status": str(raw.get("availability_status") or "unknown").strip(),
        "is_owner_camp": False,
        "source_payload": raw,
        "source_updated_at": _parse_date(raw.get("updated_at")),
        "sync_hash": compute_sync_hash({
            "external_id": external_id,
            "title": title,
            "start_date": start.isoformat() if start else "",
            "end_date": end.isoformat() if end else "",
            "price_from": price_from,
            "country": raw.get("country"),
            "city": raw.get("city"),
            "sport": sport,
            "availability_status": raw.get("availability_status"),
        }),
        "normalized_title_key": normalized_title_key(title),
    }
