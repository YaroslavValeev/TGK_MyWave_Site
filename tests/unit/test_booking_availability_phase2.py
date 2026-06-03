"""Phase 2 availability engine unit tests (pure logic + flag wiring)."""

from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from app.config.booking_capacity import GYM_MAX_CLIENTS_PER_SLOT
from app.config.booking_durations import BOAT_SET_MINUTES, GYM_SLOT_MINUTES
from app.services.booking.availability import (
    boat_interval_blocked,
    compute_max_set_count,
    count_gym_occupancy,
    intervals_overlap,
    is_boat_range_available,
    is_gym_slot_available,
    travel_buffer_blocked,
)
from app.services.booking.calendar_reader import BusyInterval, parse_service_type


TZ = ZoneInfo("Europe/Moscow")


def _dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 6, 12, hour, minute, tzinfo=TZ)


def _iv(h1, m1, h2, m2, service_type: str) -> BusyInterval:
    return BusyInterval(_dt(h1, m1), _dt(h2, m2), service_type)


class TestOverlap:
    def test_overlap_true(self):
        assert intervals_overlap(_dt(10), _dt(11), _dt(10, 30), _dt(11, 30))

    def test_overlap_false_adjacent(self):
        assert not intervals_overlap(_dt(10), _dt(11), _dt(11), _dt(12))


class TestBoatExclusive:
    def test_single_boat_event_blocks_slot(self):
        intervals = [_iv(18, 0, 18, 30, "boat")]
        assert boat_interval_blocked(intervals, _dt(18), _dt(18, 30))

    def test_multi_set_range_blocked(self):
        intervals = [_iv(18, 0, 19, 0, "boat")]
        assert boat_interval_blocked(intervals, _dt(18), _dt(18, 30))
        assert boat_interval_blocked(intervals, _dt(18, 30), _dt(19))

    def test_no_overlap_allows(self):
        intervals = [_iv(18, 0, 19, 0, "boat")]
        assert not boat_interval_blocked(intervals, _dt(19), _dt(19, 30))


class TestGymCapacity:
    def test_occupancy_counts_overlapping_gym_events(self):
        intervals = [
            _iv(10, 0, 11, 30, "gym"),
            _iv(10, 0, 11, 30, "gym"),
            _iv(10, 0, 11, 30, "gym"),
        ]
        assert (
            count_gym_occupancy(intervals, _dt(10), _dt(11, 30)) == 3
        )

    def test_three_of_four_available(self):
        intervals = [
            _iv(10, 0, 11, 30, "gym"),
            _iv(10, 0, 11, 30, "gym"),
            _iv(10, 0, 11, 30, "gym"),
        ]
        ok, remaining = is_gym_slot_available(
            "2026-06-12",
            "10:00",
            intervals,
            tz=TZ,
        )
        assert ok is True
        assert remaining == 1

    def test_four_of_four_blocked(self):
        intervals = [_iv(10, 0, 11, 30, "gym") for _ in range(4)]
        ok, remaining = is_gym_slot_available(
            "2026-06-12",
            "10:00",
            intervals,
            tz=TZ,
        )
        assert ok is False
        assert remaining == 0
        assert GYM_MAX_CLIENTS_PER_SLOT == 4


class TestTravelBuffer:
    def test_boat_then_gym_blocked_within_buffer(self):
        intervals = [_iv(12, 0, 12, 30, "boat")]
        assert travel_buffer_blocked(
            intervals, _dt(13), _dt(14, 30), "gym", enabled=True
        )

    def test_boat_then_gym_allowed_after_buffer(self):
        intervals = [_iv(12, 0, 12, 30, "boat")]
        assert not travel_buffer_blocked(
            intervals, _dt(14, 30), _dt(16), "gym", enabled=True
        )

    def test_same_type_no_buffer(self):
        intervals = [_iv(12, 0, 12, 30, "boat")]
        assert not travel_buffer_blocked(
            intervals, _dt(12, 30), _dt(13), "boat", enabled=True
        )

    def test_buffer_disabled(self):
        intervals = [_iv(12, 0, 12, 30, "boat")]
        assert not travel_buffer_blocked(
            intervals, _dt(13), _dt(14, 30), "gym", enabled=False
        )


class TestMultiSet:
    def test_max_set_count_adjacent_free(self):
        intervals = []
        assert (
            compute_max_set_count("2026-06-12", "18:00", intervals, tz=TZ) >= 2
        )

    def test_max_set_count_stops_at_conflict(self):
        intervals = [_iv(18, 30, 19, 0, "boat")]
        assert compute_max_set_count("2026-06-12", "18:00", intervals, tz=TZ) == 1

    def test_is_boat_range_available_three_sets(self):
        intervals = []
        assert is_boat_range_available(
            "2026-06-12", "15:00", 3, intervals, tz=TZ
        )


class TestParseServiceType:
    def test_extended_properties(self):
        event = {
            "summary": "x",
            "extendedProperties": {"private": {"service_type": "boat"}},
            "start": {"dateTime": "2026-06-12T15:00:00+03:00"},
            "end": {"dateTime": "2026-06-12T15:30:00+03:00"},
        }
        assert parse_service_type(event) == "boat"

    def test_summary_v2_gym(self):
        event = {
            "summary": "Тренировка — Зал — Иван (WEB_ID: bk_x)",
            "start": {"dateTime": "2026-06-12T10:00:00+03:00"},
            "end": {"dateTime": "2026-06-12T11:30:00+03:00"},
        }
        assert parse_service_type(event) == "gym"


class TestFlagOffRegression:
    def test_get_boat_slots_uses_sheets_when_flag_off(self, app, monkeypatch):
        monkeypatch.delenv("BOOKING_PHASE2_AVAILABILITY", raising=False)
        bookings = [
            {
                "date": "2026-06-12",
                "time": "09:00",
                "service_type": "boat",
                "status": "booked",
            }
        ]
        with app.app_context():
            app.config["SPREADSHEET_ID"] = "test-sheet"
            with patch(
                "app.routes.calendar_routes.read_records",
                return_value=bookings,
            ):
                from app.routes.calendar_routes import get_boat_slots

                slots = get_boat_slots("2026-06-12")
        times = [s["time"] for s in slots]
        assert "09:00" not in times
