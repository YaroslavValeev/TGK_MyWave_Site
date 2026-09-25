"""Контракт hero «Записаться» (зеркало static/js/booking.js)."""

import re
from pathlib import Path

BOOKING_JS = Path(__file__).resolve().parents[2] / "static" / "js" / "booking.js"


def resolve_hero_booking_service(
    appointment_date_iso: str | None = None,
    *,
    today_iso: str | None = None,
    season: dict | None = None,
) -> str:
    """Услуга по дате визита; если дата не выбрана — по «сегодня» (открытие модалки)."""
    ref = (appointment_date_iso or today_iso or "").strip()[:10]
    if not ref:
        raise ValueError("appointment_date_iso or today_iso required")
    if season and season["start"] <= ref <= season["end"]:
        return "boat"
    return "gym"


SUMMER_2026 = {"start": "2026-06-01", "end": "2026-09-15"}


def test_booking_js_boat_season_closed_hero_goes_to_gym():
    src = BOOKING_JS.read_text(encoding="utf-8")
    assert re.search(r"const HERO_BOAT_SEASON = null;", src), (
        "Сезон катера закрыт: hero «Записаться» должен вести в зал"
    )


def test_gym_is_first_service_card_and_boat_kept(client):
    html = client.get("/").get_data(as_text=True)
    order = re.findall(r'class="service-card js-expandable-card[^"]*"[^>]*data-service="([a-z_]+)"', html)
    assert order[0] == "gym"
    assert "boat" in order


def test_hero_without_season_is_always_gym():
    assert resolve_hero_booking_service("2026-07-10") == "gym"
    assert resolve_hero_booking_service(today_iso="2026-09-25") == "gym"


def test_hero_boat_inside_season_window():
    assert resolve_hero_booking_service("2026-06-01", season=SUMMER_2026) == "boat"
    assert resolve_hero_booking_service("2026-09-15", season=SUMMER_2026) == "boat"


def test_hero_gym_outside_season_window():
    assert resolve_hero_booking_service("2026-05-31", season=SUMMER_2026) == "gym"
    assert resolve_hero_booking_service("2026-09-16", season=SUMMER_2026) == "gym"


def test_hero_may_today_june_visit_is_boat():
    """Сегодня май, дата записи 10.06 — катер (не зал)."""
    assert resolve_hero_booking_service("2026-06-10", today_iso="2026-05-17", season=SUMMER_2026) == "boat"
    assert resolve_hero_booking_service("2026-05-20", today_iso="2026-05-17", season=SUMMER_2026) == "gym"
