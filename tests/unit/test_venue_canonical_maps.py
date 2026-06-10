"""GM canonical venue map URLs (Step 5 prep)."""

from app.config.booking_venues import BOOKING_VENUES
from app.config.venue import MYWAVE_VENUE
from app.services.booking.constants import BOAT_CALENDAR_LOCATION

GM_GYM_MAP = "https://yandex.ru/maps/-/CPh6b6jY"
GM_BOAT_MAP = (
    "https://yandex.ru/maps/org/mywave_wake/90003306477"
    "?si=1zaxyu7g67ct9pe6658pvtewag"
)


def test_gym_yandex_maps_url_canonical():
    assert BOOKING_VENUES["gym"]["yandex_maps_url"] == GM_GYM_MAP


def test_boat_yandex_maps_url_canonical():
    assert BOOKING_VENUES["boat"]["yandex_maps_url"] == GM_BOAT_MAP
    assert MYWAVE_VENUE["yandex_maps_url"] == GM_BOAT_MAP


def test_boat_calendar_location_includes_canonical_url():
    assert GM_BOAT_MAP in BOAT_CALENDAR_LOCATION
