"""Контракт hero «Записаться» (зеркало static/js/booking.js)."""

HERO_BOAT_SEASON_START = "2026-06-01"


def resolve_hero_booking_service(
    appointment_date_iso: str | None = None,
    *,
    today_iso: str | None = None,
) -> str:
    """Услуга по дате визита; если дата не выбрана — по «сегодня» (открытие модалки)."""
    ref = (appointment_date_iso or today_iso or "").strip()[:10]
    if not ref:
        raise ValueError("appointment_date_iso or today_iso required")
    return "boat" if ref >= HERO_BOAT_SEASON_START else "gym"


def test_hero_booking_gym_before_june_visit():
    assert resolve_hero_booking_service("2026-05-17") == "gym"
    assert resolve_hero_booking_service("2026-05-31") == "gym"


def test_hero_booking_boat_from_june_first_visit():
    assert resolve_hero_booking_service("2026-06-01") == "boat"
    assert resolve_hero_booking_service("2026-06-10") == "boat"


def test_hero_may_today_june_visit_is_boat():
    """Сегодня май, дата записи 10.06 — катер (не зал)."""
    assert resolve_hero_booking_service("2026-06-10", today_iso="2026-05-17") == "boat"
    assert resolve_hero_booking_service("2026-05-20", today_iso="2026-05-17") == "gym"


def test_hero_modal_open_before_june_defaults_gym():
    assert resolve_hero_booking_service(today_iso="2026-05-17") == "gym"
