"""Public camp showcase: server-side Tour Camp API → view models for /camps."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from app.services.camps.normalize import normalize_tour_camp
from app.services.camps.schema import (
    AVAILABILITY_LABELS,
    CONTENT_RIGHTS,
    SPORT_LABELS,
)
from app.services.camps.tour_client import TourCampFetchError, fetch_tour_camp_detail, fetch_tour_camps

logger = logging.getLogger(__name__)

NON_PUBLIC_PUBLICATION = frozenset({
    "draft",
    "pending_review",
    "hidden",
    "archived",
    "cancelled",
    "possible_duplicate",
})

_SHOWCASE_SPORTS = frozenset({"wakesurf", "wakeboard", "mixed"})


@dataclass
class ShowcaseListResult:
    state: str
    camps: List[Dict[str, Any]] = field(default_factory=list)
    message: str = ""


@dataclass
class ShowcaseDetailResult:
    state: str
    camp: Optional[Dict[str, Any]] = None
    message: str = ""


def _error_state(exc: TourCampFetchError) -> str:
    if exc.kind == "auth":
        return "error_auth"
    if exc.kind == "server":
        return "error_server"
    if exc.kind in ("timeout", "client"):
        return "error_unavailable"
    return "error_unavailable"


def _error_message(state: str) -> str:
    return {
        "error_auth": "Не удалось авторизоваться в каталоге кемпов. Проверьте настройки интеграции.",
        "error_server": "Каталог кемпов временно недоступен из‑за ошибки на стороне Tour API.",
        "error_unavailable": "Каталог кемпов временно недоступен. Попробуйте позже.",
    }.get(state, "Не удалось загрузить каталог кемпов.")


def _map_content_rights(raw: Any) -> str:
    s = str(raw or "").strip().lower()
    if s in CONTENT_RIGHTS:
        return s
    return "unknown"


def _raw_sports(raw: Dict[str, Any]) -> set[str]:
    sport = raw.get("sport") or raw.get("sports")
    if isinstance(sport, list):
        return {str(item).strip().lower() for item in sport if str(item).strip()}
    if sport:
        return {str(sport).strip().lower()}
    return set()


def _matches_showcase_sport(raw: Dict[str, Any]) -> bool:
    sports = _raw_sports(raw)
    if not sports:
        return True
    return bool(sports & _SHOWCASE_SPORTS)


def _matches_showcase_audience(raw: Dict[str, Any]) -> bool:
    audience = raw.get("audience_language") or raw.get("audience") or []
    if isinstance(audience, str):
        audience = [audience]
    if not audience:
        return True
    langs = {str(item).strip().lower() for item in audience if str(item).strip()}
    return "ru" in langs


def _parse_camp_date(value: Any) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return _parse_iso_date(str(value).strip())


def _camp_active_until(raw: Dict[str, Any]) -> Optional[date]:
    """Last calendar day the camp is considered current (end_date, else start_date)."""
    end = _parse_camp_date(raw.get("end_date"))
    if end is not None:
        return end
    return _parse_camp_date(raw.get("start_date"))


def _matches_showcase_schedule(raw: Dict[str, Any], *, today: Optional[date] = None) -> bool:
    """Hide finished camps; keep current and upcoming. No dates → keep (unknown schedule)."""
    active_until = _camp_active_until(raw)
    if active_until is None:
        return True
    return active_until >= (today or date.today())


def is_showcase_public(raw: Dict[str, Any], *, today: Optional[date] = None) -> bool:
    pub = str(raw.get("publication_status") or raw.get("tour_publication_status") or "published").strip().lower()
    if pub in NON_PUBLIC_PUBLICATION:
        return False
    if pub and pub != "published":
        return False
    if _map_content_rights(raw.get("content_rights_status")) == "restricted":
        return False
    if not _matches_showcase_sport(raw):
        return False
    if not _matches_showcase_audience(raw):
        return False
    if not _matches_showcase_schedule(raw, today=today):
        return False
    return bool(str(raw.get("id") or raw.get("external_id") or "").strip() or str(raw.get("title") or "").strip())


def _format_date(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]


def _format_dates(start: Any, end: Any) -> Optional[str]:
    s, e = _format_date(start), _format_date(end)
    if s and e and s != e:
        return f"{s} — {e}"
    return s or e


def _format_duration(duration_days: Any, start: Any, end: Any) -> Optional[str]:
    try:
        days = int(duration_days) if duration_days not in (None, "") else None
    except (TypeError, ValueError):
        days = None
    if days and days > 0:
        return f"{days} дн."
    s, e = start, end
    if isinstance(s, str):
        s = _parse_iso_date(s)
    if isinstance(e, str):
        e = _parse_iso_date(e)
    if isinstance(s, date) and isinstance(e, date) and e >= s:
        delta = (e - s).days + 1
        if delta > 0:
            return f"{delta} дн."
    return None


def _parse_iso_date(value: str) -> Optional[date]:
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _format_location(country: Any, city: Any, location_name: Any) -> Optional[str]:
    parts = [str(p).strip() for p in (city, country, location_name) if p and str(p).strip()]
    if not parts:
        return None
    seen: list[str] = []
    for part in parts:
        if part not in seen:
            seen.append(part)
    return ", ".join(seen)


def _format_price(price_from: Any, price_to: Any, currency: Any) -> Optional[str]:
    cur = str(currency or "RUB").strip()
    symbol = "₽" if cur.upper() in ("RUB", "RUR") else cur
    try:
        pf = int(price_from) if price_from not in (None, "") else None
    except (TypeError, ValueError):
        pf = None
    try:
        pt = int(price_to) if price_to not in (None, "") else None
    except (TypeError, ValueError):
        pt = None
    if pf is not None and pt is not None and pt > pf:
        return f"{pf:,}".replace(",", " ") + f"–{pt:,}".replace(",", " ") + f" {symbol}"
    if pf is not None:
        return f"от {pf:,}".replace(",", " ") + f" {symbol}"
    return None


def _source_badge(content_rights: str, is_owner_camp: bool) -> str:
    if is_owner_camp:
        return "MyWave Camp"
    if content_rights == "partner_allowed":
        return "Партнёрский"
    if content_rights == "owned":
        return "MyWave Camp"
    return "Из MyWaveTour"


def _partnership_confirmed(content_rights: str, is_owner_camp: bool) -> bool:
    if is_owner_camp:
        return True
    return content_rights in ("owned", "partner_allowed")


def _program_text(raw: Dict[str, Any], normalized: Dict[str, Any]) -> Optional[str]:
    program = raw.get("program") or raw.get("programme") or raw.get("schedule") or normalized.get("program")
    if isinstance(program, list):
        lines = [str(item).strip() for item in program if str(item).strip()]
        return "\n".join(lines) if lines else None
    if program:
        return str(program).strip() or None
    return None


def to_showcase_view(raw: Dict[str, Any], normalized: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    norm = normalized or normalize_tour_camp(raw)
    rights = norm.get("content_rights_status") or "unknown"
    owner = bool(norm.get("is_owner_camp"))
    start, end = norm.get("start_date"), norm.get("end_date")
    return {
        "id": norm.get("external_id") or str(raw.get("id") or "").strip(),
        "slug": norm.get("slug"),
        "title": norm.get("title") or "Кемп",
        "short_description": norm.get("short_description"),
        "description": norm.get("description"),
        "sport": norm.get("sport"),
        "sport_label": SPORT_LABELS.get(norm.get("sport") or "", norm.get("sport") or ""),
        "level": norm.get("level"),
        "country": norm.get("country"),
        "city": norm.get("city"),
        "location_name": norm.get("location_name"),
        "location_label": _format_location(norm.get("country"), norm.get("city"), norm.get("location_name")),
        "start_date": _format_date(start),
        "end_date": _format_date(end),
        "dates_label": _format_dates(start, end),
        "duration_label": _format_duration(norm.get("duration_days"), start, end),
        "price_from": norm.get("price_from"),
        "price_to": norm.get("price_to"),
        "currency": norm.get("currency"),
        "price_label": _format_price(norm.get("price_from"), norm.get("price_to"), norm.get("currency")),
        "availability_status": norm.get("availability_status"),
        "availability_label": AVAILABILITY_LABELS.get(norm.get("availability_status") or "unknown", "Уточняется"),
        "included": norm.get("included"),
        "not_included": norm.get("not_included"),
        "organizer_name": norm.get("organizer_name"),
        "organizer_type": norm.get("organizer_type"),
        "program": _program_text(raw, norm),
        "gallery": norm.get("gallery") or [],
        "video_url": norm.get("video_url"),
        "cover_image_url": norm.get("cover_image_url"),
        "booking_url": norm.get("booking_url"),
        "source_url": norm.get("source_url"),
        "source_badge": _source_badge(rights, owner),
        "partnership_confirmed": _partnership_confirmed(rights, owner),
        "content_rights_status": rights,
        "content_rights_notice": (
            None
            if _partnership_confirmed(rights, owner)
            else "Партнёрство с MyWave не подтверждено — программа опубликована как справочная информация из Tour."
        ),
        "publication_status": norm.get("tour_publication_status") or raw.get("publication_status"),
    }


def fetch_showcase_camps() -> ShowcaseListResult:
    try:
        raw_items = fetch_tour_camps()
    except TourCampFetchError as exc:
        state = _error_state(exc)
        return ShowcaseListResult(state=state, message=_error_message(state))

    camps = [to_showcase_view(raw) for raw in raw_items if is_showcase_public(raw)]
    if not camps:
        return ShowcaseListResult(state="empty", camps=[], message="Пока нет опубликованных кемпов.")
    return ShowcaseListResult(state="ok", camps=camps)


def _find_camp_in_showcase_list(camp_id: str) -> Optional[Dict[str, Any]]:
    try:
        raw_items = fetch_tour_camps()
    except TourCampFetchError:
        return None

    for raw in raw_items:
        raw_id = str(raw.get("id") or raw.get("external_id") or "").strip()
        if raw_id == camp_id:
            return raw
    return None


def fetch_showcase_detail(camp_id: str) -> ShowcaseDetailResult:
    camp_id = str(camp_id or "").strip()
    if not camp_id:
        return ShowcaseDetailResult(state="not_found", message="Кемп не найден.")

    try:
        raw = fetch_tour_camp_detail(camp_id)
    except TourCampFetchError as exc:
        if exc.status_code == 404:
            raw = _find_camp_in_showcase_list(camp_id)
            if raw is None:
                logger.warning(
                    "camp_detail_not_found",
                    extra={"camp_id": camp_id, "source": "tour_detail_404"},
                )
                return ShowcaseDetailResult(state="not_found", message="Кемп не найден.")
            logger.warning(
                "camp_detail_fallback_list",
                extra={
                    "camp_id": camp_id,
                    "source": "list_fallback",
                    "tour_status": exc.status_code,
                },
            )
        else:
            state = _error_state(exc)
            return ShowcaseDetailResult(state=state, message=_error_message(state))

    if not is_showcase_public(raw):
        return ShowcaseDetailResult(state="not_found", message="Кемп недоступен для публичного просмотра.")

    return ShowcaseDetailResult(state="ok", camp=to_showcase_view(raw))


def fetch_showcase_preview(limit: int = 3) -> List[Dict[str, Any]]:
    """Best-effort preview for home page; never raises."""
    try:
        result = fetch_showcase_camps()
    except Exception:
        return []
    if result.state != "ok":
        return []
    return result.camps[: max(0, limit)]
