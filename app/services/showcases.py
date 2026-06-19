"""Showcase configuration loader and helper utilities."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from flask import current_app, url_for

from app.seo.schema_org import build_showcase_graph, build_event_list

BASE_DIR = Path(__file__).resolve().parents[2]
SHOWCASE_DIR = BASE_DIR / 'configs' / 'showcases'


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
    route: str = '/projects'
    channels: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    itinerary: list[dict[str, Any]] = field(default_factory=list)
    leaderboard: list[dict[str, Any]] = field(default_factory=list)
    checklist: list[str] = field(default_factory=list)

    @property
    def url(self) -> str:
        if self.route and self.route != '/projects':
            return f"{self.route.rstrip('/')}/{self.slug}"
        return f"/projects/{self.slug}"

    def as_card(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'slug': self.slug,
            'name': self.name,
            'summary': self.summary,
            'city': self.city,
            'country': self.country,
            'tags': self.tags,
            'has_detail': False,
            'cover': self.cover_image,
            'images': self.gallery,
            'cta_url': self.cta_url,
            'category': self.category,
            'level': self.level,
            'price_from': self.price_from,
            'checklist': self.checklist,
        }

    def as_schema_payload(self, base_route: str) -> dict[str, Any]:
        payload = asdict(self)
        payload['cover'] = self.cover_image
        payload['absolute_url'] = url_for('projects_page', _external=True) + f"#{self.slug}"
        payload['url'] = self.url if self.url.startswith('http') else f"{base_route.rstrip('/')}/{self.slug}"
        return payload


@lru_cache(maxsize=1)
def load_showcase_configs() -> dict[str, ShowcaseConfig]:
    configs: dict[str, ShowcaseConfig] = {}
    if not SHOWCASE_DIR.exists():
        return configs
    for path in sorted(SHOWCASE_DIR.glob('*.y*ml')):
        with path.open('r', encoding='utf-8') as fh:
            data = yaml.safe_load(fh) or {}
        if not data:
            continue
        cfg = ShowcaseConfig(**data)
        configs[cfg.id] = cfg
    return configs


def list_showcases(channel: str | None = None, kind: str | None = None) -> list[ShowcaseConfig]:
    configs = load_showcase_configs()
    showcases = list(configs.values())
    if channel:
        showcases = [sc for sc in showcases if channel in (sc.channels or ['projects'])]
    if kind:
        showcases = [sc for sc in showcases if sc.kind == kind]
    return showcases


def get_showcase(showcase_id: str) -> ShowcaseConfig | None:
    configs = load_showcase_configs()
    return configs.get(showcase_id)


from app.services.images_resolver import resolve_card_images, FALLBACK as FALLBACK_IMG, rotate_images_to_cover_index


def _ensure_images_resolved(cards: list[dict[str, Any]]) -> None:
    """P0-1: карточка получает images[], cover=images[0], fallback=Place1Logo.png.
    Источник — скан папки. src всегда файл, не папка."""
    for card in cards:
        raw = (card.get('cover') or '').strip()
        if not raw or raw.startswith('http'):
            card['cover'] = FALLBACK_IMG
            card['images'] = [FALLBACK_IMG]
            card['fallback'] = FALLBACK_IMG
            continue
        rel = raw.replace('/static/', '').replace('static/', '').lstrip('/')
        resolved = resolve_card_images(rel, fallback=FALLBACK_IMG)
        card['cover'] = resolved['cover']
        card['images'] = resolved['images']
        card['fallback'] = resolved['fallback']


def _normalize_checklist_cover(cards: list[dict[str, Any]]) -> None:
    """Checklist folder scan sorts ChatGPT PNG before Check1; prefer cropped cover."""
    for card in cards:
        if card.get('id') != 'checklist':
            continue
        imgs = list(card.get('images') or [])
        if len(imgs) < 2:
            continue
        preferred = next(
            (p for p in imgs if p.rsplit('/', 1)[-1].lower() == 'check1.png'),
            None,
        )
        if not preferred or imgs[0] == preferred:
            continue
        idx = imgs.index(preferred)
        rotated = rotate_images_to_cover_index(imgs, idx)
        card['images'] = rotated
        card['cover'] = rotated[0]


# Канонический порядок проектов на витрине
_PROJECT_ORDER = ['wake_challenge', 'wakesurf_safari', 'checklist', 'mywave_ruza_camp']


def get_project_cards() -> list[dict[str, Any]]:
    showcases = list_showcases(channel='projects')
    by_id = {sc.id: sc for sc in showcases}
    ordered = []
    for pid in _PROJECT_ORDER:
        if pid in by_id:
            ordered.append(by_id[pid])
    for sc in showcases:
        if sc.id not in _PROJECT_ORDER:
            ordered.append(sc)
    cards = []
    for sc in ordered:
        card = sc.as_card()
        # WakeSurf Challenge: ссылка на полную страницу проекта
        if sc.id == 'wake_challenge':
            card['url'] = '/projects/wakesurf-challenge-2025'
            meta = sc.metadata or {}
            card['lead'] = meta.get('lead', '')
            card['microfacts'] = meta.get('microfacts', [])
            card['expanded'] = meta.get('expanded', {})
        elif sc.id == 'mywave_ruza_camp':
            card['url'] = '/projects/mywave-ruza-camp'
            meta = sc.metadata or {}
            card['lead'] = meta.get('lead', '')
            card['microfacts'] = meta.get('microfacts', [])
            card['bullets'] = meta.get('bullets', [])
            card['expanded'] = meta.get('expanded', {})
        elif sc.id == 'wakesurf_safari':
            card['url'] = '/projects/wakesurf-safari'
            meta = sc.metadata or {}
            card['lead'] = meta.get('lead', '')
            card['microfacts'] = meta.get('microfacts', [])
            card['bullets'] = meta.get('bullets', [])
            card['expanded'] = meta.get('expanded', {})
        elif sc.id == 'checklist':
            card['url'] = '/projects/checklist-org'
            meta = sc.metadata or {}
            card['expanded'] = meta.get('expanded', {})
        else:
            card['url'] = f"/projects/{sc.slug}"
        cards.append(card)
    _ensure_images_resolved(cards)
    _normalize_checklist_cover(cards)
    return cards


def get_projects_graph() -> dict[str, Any]:
    showcases = [sc.as_schema_payload(url_for('projects_page', _external=True)) for sc in list_showcases(channel='projects')]
    return build_showcase_graph(showcases)


def get_events_schema() -> list[dict[str, Any]]:
    events = [sc.as_schema_payload(url_for('events_page', _external=True)) for sc in list_showcases(channel='events')]
    return build_event_list(events)


def get_event_cards() -> list[dict[str, Any]]:
    cards = []
    for sc in list_showcases(channel='events'):
        card = sc.as_card()
        card['date_range'] = f"{sc.start_date} — {sc.end_date}" if sc.start_date and sc.end_date else sc.start_date
        card['url'] = sc.url
        cards.append(card)
    return cards


def get_showcase_itinerary(showcase_id: str, date: str | None = None) -> dict[str, Any]:
    sc = get_showcase(showcase_id)
    if not sc:
        raise ValueError(f'Showcase {showcase_id} not found')
    items = sc.itinerary
    if date:
        items = [step for step in items if str(step.get('day')) == date or step.get('date') == date]
    return {'showcase_id': showcase_id, 'itinerary': items}


def get_challenge_leaderboard(showcase_id: str, limit: int = 10) -> dict[str, Any]:
    sc = get_showcase(showcase_id)
    if not sc:
        raise ValueError(f'Showcase {showcase_id} not found')
    board = sc.leaderboard[:limit]
    return {'showcase_id': showcase_id, 'entries': board}


def _log_analytics(event: str, meta: dict[str, Any]) -> None:
    try:
        from app.services.google_sheets_service import log_analytics_event

        log_analytics_event({
            'event': event,
            'context': meta.get('showcase_id'),
            'user_key': meta.get('user_phone') or meta.get('user_email', ''),
            'type': meta.get('channel', ''),
            'meta': meta,
            'ip': meta.get('ip', ''),
            'user_agent': meta.get('user_agent', ''),
        })
    except Exception as exc:
        current_app.logger.warning('Failed to log analytics event %s: %s', event, exc)


def create_showcase_booking(showcase_id: str, slot: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
    sc = get_showcase(showcase_id)
    if not sc:
        raise ValueError(f'Showcase {showcase_id} not found')
    date = slot.get('date') or sc.start_date
    time = slot.get('time') or '09:00'
    workout_id = None
    try:
        from app.modules.calendar_integration import create_workout_if_not_exists

        workout_id = create_workout_if_not_exists(date, time, showcase_id=showcase_id, slot_type=sc.category)
    except Exception as exc:
        current_app.logger.warning('Calendar write failed: %s', exc)
    meta = {
        'showcase_id': showcase_id,
        'channel': user.get('channel', 'web'),
        'trip_date': date,
        'user_name': user.get('name'),
        'user_phone': user.get('phone'),
        'origin': user.get('origin', 'site'),
    }
    _log_analytics('safari_booking_created', meta)
    return {
        'success': True,
        'showcase_id': showcase_id,
        'workout_id': workout_id,
        'slot': {'date': date, 'time': time},
        'message': f"Бронь для {sc.name} принята. Мы свяжемся по номеру {user.get('phone')}.",
    }


def join_challenge(showcase_id: str, participant: dict[str, Any]) -> dict[str, Any]:
    sc = get_showcase(showcase_id)
    if not sc:
        raise ValueError(f'Showcase {showcase_id} not found')
    entry = {
        'name': participant.get('name'),
        'city': participant.get('city'),
        'experience_level': participant.get('experience_level'),
    }
    _log_analytics('challenge_joined', {'showcase_id': showcase_id, 'participant': entry, 'channel': participant.get('channel', 'web')})
    return {'ok': True, 'showcase_id': showcase_id, 'participant': entry}
