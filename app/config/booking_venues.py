"""Venue config for booking (Зал / Катер) — Phase 2 confirmation + Calendar location."""

from __future__ import annotations

from app.config.venue import MYWAVE_VENUE
from app.services.booking.constants import BOAT_CALENDAR_LOCATION

# Зал (gym) — Phase 2 v2 location + confirmation UX
GYM_VENUE = {
    "service_type": "gym",
    "location_label": "Зал",
    "calendar_location_v2": "Зал",
    "latitude": 55.777052,
    "longitude": 37.502594,
    "yandex_maps_url": "https://yandex.ru/maps/-/CLWQy6-I",
}

# Катер (boat) — Phase 1 location unchanged in production until SUMMARY/location flags ON
BOAT_VENUE = {
    "service_type": "boat",
    "location_label": "Катер",
    "calendar_location": BOAT_CALENDAR_LOCATION,
    "yandex_maps_url": MYWAVE_VENUE["yandex_maps_url"],
    "latitude": MYWAVE_VENUE["latitude"],
    "longitude": MYWAVE_VENUE["longitude"],
}

BOOKING_VENUES = {
    "gym": GYM_VENUE,
    "boat": BOAT_VENUE,
}
