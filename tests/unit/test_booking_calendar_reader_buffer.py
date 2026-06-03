"""Calendar reader: travel-buffer query window (PR16 TGbotAdmin blocker 2)."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from app.config.booking_durations import TRAINER_TRAVEL_BUFFER_MINUTES
from app.services.booking.availability import SlotUnavailableError, assert_booking_available
from app.services.booking.calendar_reader import (
    BusyInterval,
    day_bounds,
    day_bounds_with_buffer,
    list_busy_intervals_for_date,
)

TZ = ZoneInfo("Europe/Moscow")


class TestDayBoundsWithBuffer:
    def test_expands_by_120_minutes(self, app):
        with app.app_context():
            app.config["TIMEZONE"] = "Europe/Moscow"
            tmin, tmax = day_bounds_with_buffer("2026-06-15", 120, TZ)
            day_min, day_max = day_bounds("2026-06-15", TZ)
            assert tmin == datetime(2026, 6, 14, 22, 0, tzinfo=TZ)
            assert tmax == datetime(2026, 6, 16, 2, 0, tzinfo=TZ)
            assert tmin == day_min - timedelta(minutes=120)
            assert tmax == day_max + timedelta(minutes=120)


class TestListEventsQueryWindow:
    def test_list_uses_expanded_time_min_max_when_phase2_on(self, app, monkeypatch):
        monkeypatch.setenv("BOOKING_PHASE2_AVAILABILITY", "1")
        with app.app_context():
            app.config["GOOGLE_CALENDAR_ID"] = "cal@test"
            app.config["TIMEZONE"] = "Europe/Moscow"

            captured: dict = {}

            def fake_list(**kwargs):
                captured.update(kwargs)
                chain = MagicMock()
                chain.execute.return_value = {"items": []}
                return chain

            mock_cal = MagicMock()
            mock_cal.events.return_value.list = fake_list

            with patch(
                "app.services.google.get_google_services",
                return_value=(None, None, mock_cal),
            ):
                list_busy_intervals_for_date("2026-06-15")

            assert "timeMin" in captured and "timeMax" in captured
            tmin = datetime.fromisoformat(captured["timeMin"])
            tmax = datetime.fromisoformat(captured["timeMax"])
            expected_min, expected_max = day_bounds_with_buffer(
                "2026-06-15", TRAINER_TRAVEL_BUFFER_MINUTES, TZ
            )
            assert tmin == expected_min
            assert tmax == expected_max


class TestCrossDayTravelBufferRecheck:
    """Intervals that expanded Calendar window must include (±120 min)."""

    def test_gym_morning_blocked_by_previous_evening_boat(self, app, monkeypatch):
        monkeypatch.setenv("BOOKING_PHASE2_AVAILABILITY", "1")
        monkeypatch.setenv("BOOKING_PHASE2_TRAVEL_BUFFER", "1")
        intervals = [
            BusyInterval(
                datetime(2026, 6, 14, 21, 0, tzinfo=TZ),
                datetime(2026, 6, 14, 23, 0, tzinfo=TZ),
                "boat",
            )
        ]
        with app.app_context():
            with patch(
                "app.services.booking.availability.list_busy_intervals_for_date",
                return_value=intervals,
            ):
                with pytest.raises(SlotUnavailableError):
                    assert_booking_available("2026-06-15", "00:30", "gym")

    def test_boat_evening_blocked_by_next_morning_gym(self, app, monkeypatch):
        monkeypatch.setenv("BOOKING_PHASE2_AVAILABILITY", "1")
        monkeypatch.setenv("BOOKING_PHASE2_TRAVEL_BUFFER", "1")
        intervals = [
            BusyInterval(
                datetime(2026, 6, 16, 0, 30, tzinfo=TZ),
                datetime(2026, 6, 16, 2, 0, tzinfo=TZ),
                "gym",
            )
        ]
        with app.app_context():
            with patch(
                "app.services.booking.availability.list_busy_intervals_for_date",
                return_value=intervals,
            ):
                with pytest.raises(SlotUnavailableError):
                    # boat 22:30–23:00 + 120 min buffer overlaps gym from 00:30 next day
                    assert_booking_available("2026-06-15", "22:30", "boat", set_count=1)
