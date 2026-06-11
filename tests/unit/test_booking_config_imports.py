"""Config-layer import safety (Step 5 circular-import hotfix)."""

from app.config.booking_venues import BOOKING_VENUES
from app.services.booking.calendar_writer import get_calendar_location


def test_booking_venues_import_without_cycle():
    assert "gym" in BOOKING_VENUES
    assert "boat" in BOOKING_VENUES


def test_calendar_writer_import_without_cycle(app):
    with app.app_context():
        assert get_calendar_location("gym") == "Зал MyWave"
