"""Showcase configuration loader and helper utilities."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from flask import current_app, url_for

logger = logging.getLogger(__name__)

from app.seo.schema_org import build_showcase_graph, build_event_list

BASE_DIR = Path(__file__).resolve().parents[2]
SHOWCASE_DIR = BASE_DIR / "configs" / "showcases"


@dataclass(slots=True)
class ShowcaseConfig:
    id: str
    slug: str
    name: str
    summary: str
    description: str
    category: str
    kind: str
    schema_type: str
    status: str
    city: str
    country: str
    start_date: str
    end_date: str
    tags: list[str] = field(default_factory=list)
    level: str | None = None
    price_from: str | None = None
    capacity: int | None = None
    cover_image: str | None = None
    gallery: list[str] = field(default_factory=list)
    cta_url: str | None = None
    route: str = "/projects"
    channels: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    itinerary: list[dict[str, Any]] = field(default_factory=list)
    leaderboard: list[dict[str, Any]] = field(default_factory=list)
    # Поля для раздела «Проекты» (модалка, CTA, канонический URL страницы)
    modal_content: str | None = None
    primary_actions: list[dict[str, Any]] = field(default_factory=list)
    page_url: str | None = None

    @property
    def url(self) -> str:
        if self.route and self.route != "/projects":
            return f"{self.route.rstrip('/')}/{self.slug}"
        return f"/projects/{self.slug}"

    def as_card(self) -> dict[str, Any]:
        card: dict[str, Any] = {
            "id": self.id,
            "slug": self.slug,
            "name": self.name,
            "summary": self.summary,
            "city": self.city,
            "country": self.country,
            "tags": self.tags,
            "has_detail": False,
            "cover": self.cover_image,
            "images": self.gallery,
            "cta_url": self.cta_url,
            "category": self.category,
            "level": self.level,
            "price_from": self.price_from,
        }
        # Поля для модалки и CTA (раздел «Проекты», PROJECTS_UX_SPEC_AND_DOD)
        card["modal_content"] = self.modal_content or ""
        card["primary_actions"] = self.primary_actions if self.primary_actions is not None else []
        card["page_url"] = self.page_url if self.page_url else self.url
        return card

    def as_schema_payload(self, base_route: str) -> dict[str, Any]:
        payload = asdict(self)
        payload["cover"] = self.cover_image
        payload["absolute_url"] = (
            url_for("projects_page", _external=True) + f"#{self.slug}"
        )
        payload["url"] = (
            self.url
            if self.url.startswith("http")
            else f"{base_route.rstrip('/')}/{self.slug}"
        )
        return payload


def _normalize_value(v: Any) -> Any:
    """Приводим date/datetime к строкам для корректной JSON-сериализации в шаблонах."""
    if isinstance(v, datetime):
        return v.date().isoformat() if v else ""
    if isinstance(v, date):
        return v.isoformat() if v else ""
    return v


def _filter_showcase_data(data: dict[str, Any]) -> dict[str, Any]:
    """Оставляем только поля, известные ShowcaseConfig (защита от лишних ключей в YAML)."""
    allowed = set(ShowcaseConfig.__dataclass_fields__)
    out = {}
    for k, v in data.items():
        if k not in allowed:
            continue
        if k in ("start_date", "end_date"):
            out[k] = _normalize_value(v)
        elif k == "primary_actions":
            out[k] = v if isinstance(v, list) else []
        else:
            out[k] = v
    return out


@lru_cache(maxsize=1)
def load_showcase_configs() -> dict[str, ShowcaseConfig]:
    configs: dict[str, ShowcaseConfig] = {}
    if not SHOWCASE_DIR.exists():
        return configs
    for path in sorted(SHOWCASE_DIR.glob("*.y*ml")):
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            if not data:
                continue
            cfg = ShowcaseConfig(**_filter_showcase_data(data))
            configs[cfg.id] = cfg
        except Exception as e:
            logger.warning("Пропуск showcase %s: %s", path.name, e)
            continue
    return configs


def list_showcases(
    channel: str | None = None, kind: str | None = None
) -> list[ShowcaseConfig]:
    configs = load_showcase_configs()
    showcases = list(configs.values())
    if channel:
        showcases = [sc for sc in showcases if channel in (sc.channels or ["projects"])]
    if kind:
        showcases = [sc for sc in showcases if sc.kind == kind]
    return showcases


def get_showcase(showcase_id: str) -> ShowcaseConfig | None:
    configs = load_showcase_configs()
    return configs.get(showcase_id)


# Fallback-обложка, если файл из YAML отсутствует (убирает 404 в Network)
COVER_FALLBACK = "images/hero-wakesurf.webp"

# Порядок slug'ов для превью на главной (первые 3 показываются в карусели)
PROJECTS_PREVIEW_SLUGS = ["wsc-2026", "wakesurf-safari", "camp-ruza"]


def get_project_cards() -> list[dict[str, Any]]:
    cards = []
    static_dir = BASE_DIR / "static"
    for sc in list_showcases(channel="projects"):
        card = sc.as_card()
        card["url"] = sc.url
        cover = card.get("cover")
        if cover and not (static_dir / cover).exists():
            card["cover"] = COVER_FALLBACK
        if getattr(sc, "metadata", None) and isinstance(sc.metadata, dict):
            card["badges"] = sc.metadata.get("badges") or []
        else:
            card["badges"] = []
        cards.append(card)
    return cards


def get_project_cards_preview(limit: int = 3) -> list[dict[str, Any]]:
    """Карточки для блока «Проекты» на главной: приоритетный порядок (WSC 2026, Safari, Летний лагерь)."""
    all_cards = get_project_cards()
    by_slug = {c["slug"]: c for c in all_cards}
    ordered = []
    for slug in PROJECTS_PREVIEW_SLUGS:
        if slug in by_slug:
            ordered.append(by_slug[slug])
    for c in all_cards:
        if c["slug"] not in PROJECTS_PREVIEW_SLUGS:
            ordered.append(c)
    return ordered[:limit]


def get_projects_graph() -> dict[str, Any]:
    base = ""
    try:
        base = url_for("projects_page", _external=True)
    except Exception:
        base = "https://mywavetreaning.ru/projects"
    showcases = []
    for sc in list_showcases(channel="projects"):
        try:
            showcases.append(sc.as_schema_payload(base))
        except Exception as e:
            logger.warning("Пропуск schema для showcase %s: %s", sc.id, e)
    return build_showcase_graph(showcases)


def get_events_schema() -> list[dict[str, Any]]:
    events = [
        sc.as_schema_payload(url_for("events_page", _external=True))
        for sc in list_showcases(channel="events")
    ]
    return build_event_list(events)


def get_event_cards() -> list[dict[str, Any]]:
    cards = []
    for sc in list_showcases(channel="events"):
        card = sc.as_card()
        card["date_range"] = (
            f"{sc.start_date} — {sc.end_date}"
            if sc.start_date and sc.end_date
            else sc.start_date
        )
        card["url"] = sc.url
        cards.append(card)
    return cards


def get_showcase_itinerary(showcase_id: str, date: str | None = None) -> dict[str, Any]:
    sc = get_showcase(showcase_id)
    if not sc:
        raise ValueError(f"Showcase {showcase_id} not found")
    items = sc.itinerary
    if date:
        items = [
            step
            for step in items
            if str(step.get("day")) == date or step.get("date") == date
        ]
    return {"showcase_id": showcase_id, "itinerary": items}


def get_challenge_leaderboard(showcase_id: str, limit: int = 10) -> dict[str, Any]:
    sc = get_showcase(showcase_id)
    if not sc:
        raise ValueError(f"Showcase {showcase_id} not found")
    board = sc.leaderboard[:limit]
    return {"showcase_id": showcase_id, "entries": board}


def _log_analytics(event: str, meta: dict[str, Any]) -> None:
    try:
        from app.services.google_sheets_service import log_analytics_event

        log_analytics_event(
            {
                "event": event,
                "context": meta.get("showcase_id"),
                "user_key": meta.get("user_phone") or meta.get("user_email", ""),
                "type": meta.get("channel", ""),
                "meta": meta,
                "ip": meta.get("ip", ""),
                "user_agent": meta.get("user_agent", ""),
            }
        )
    except Exception as exc:
        current_app.logger.warning("Failed to log analytics event %s: %s", event, exc)


def create_showcase_booking(
    showcase_id: str, slot: dict[str, Any], user: dict[str, Any]
) -> dict[str, Any]:
    sc = get_showcase(showcase_id)
    if not sc:
        raise ValueError(f"Showcase {showcase_id} not found")
    date = slot.get("date") or sc.start_date
    time = slot.get("time") or "09:00"
    workout_id = None
    try:
        from app.modules.calendar_integration import create_workout_if_not_exists

        workout_id = create_workout_if_not_exists(
            date, time, showcase_id=showcase_id, slot_type=sc.category
        )
    except Exception as exc:
        current_app.logger.warning("Calendar write failed: %s", exc)
    meta = {
        "showcase_id": showcase_id,
        "channel": user.get("channel", "web"),
        "trip_date": date,
        "user_name": user.get("name"),
        "user_phone": user.get("phone"),
        "origin": user.get("origin", "site"),
    }
    _log_analytics("safari_booking_created", meta)
    return {
        "success": True,
        "showcase_id": showcase_id,
        "workout_id": workout_id,
        "slot": {"date": date, "time": time},
        "message": f"Бронь для {sc.name} принята. Мы свяжемся по номеру {user.get('phone')}.",
    }


def join_challenge(showcase_id: str, participant: dict[str, Any]) -> dict[str, Any]:
    sc = get_showcase(showcase_id)
    if not sc:
        raise ValueError(f"Showcase {showcase_id} not found")
    entry = {
        "name": participant.get("name"),
        "city": participant.get("city"),
        "experience_level": participant.get("experience_level"),
    }
    _log_analytics(
        "challenge_joined",
        {
            "showcase_id": showcase_id,
            "participant": entry,
            "channel": participant.get("channel", "web"),
        },
    )
    return {"ok": True, "showcase_id": showcase_id, "participant": entry}
