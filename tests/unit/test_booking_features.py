"""Phase 2 booking flags and capacity constants (PR1 — no runtime behavior change)."""

import pytest

from app.config.booking_capacity import (
    BOAT_MAX_CLIENTS_PER_SLOT,
    GYM_MAX_CLIENTS_PER_SLOT,
)
from app.config.booking_durations import (
    BOAT_SET_MINUTES,
    GYM_SLOT_MINUTES,
    TRAINER_TRAVEL_BUFFER_MINUTES,
    BOOKING_DURATION_MINUTES,
)
from app.config.booking_features import (
    get_booking_phase2_flags,
    is_phase2_availability_enabled,
    is_phase2_gym_location_v2_enabled,
    is_phase2_multi_set_boat_enabled,
    is_phase2_summary_v2_enabled,
    is_phase2_travel_buffer_enabled,
)
from app.config.booking_venues import BOAT_VENUE, BOOKING_VENUES, GYM_VENUE


class TestPhase2FlagsDefaultOff:
    def test_all_flags_off_by_default(self, monkeypatch):
        for key in (
            "BOOKING_PHASE2_AVAILABILITY",
            "BOOKING_PHASE2_TRAVEL_BUFFER",
            "BOOKING_PHASE2_MULTI_SET_BOAT",
            "BOOKING_PHASE2_SUMMARY_V2",
            "BOOKING_PHASE2_GYM_LOCATION_V2",
        ):
            monkeypatch.delenv(key, raising=False)

        flags = get_booking_phase2_flags()
        assert flags == {
            "BOOKING_PHASE2_AVAILABILITY": False,
            "BOOKING_PHASE2_TRAVEL_BUFFER": False,
            "BOOKING_PHASE2_MULTI_SET_BOAT": False,
            "BOOKING_PHASE2_SUMMARY_V2": False,
            "BOOKING_PHASE2_GYM_LOCATION_V2": False,
        }

    def test_truthy_env_values(self, monkeypatch):
        monkeypatch.setenv("BOOKING_PHASE2_AVAILABILITY", "1")
        monkeypatch.setenv("BOOKING_PHASE2_TRAVEL_BUFFER", "true")
        monkeypatch.setenv("BOOKING_PHASE2_MULTI_SET_BOAT", "yes")
        monkeypatch.setenv("BOOKING_PHASE2_SUMMARY_V2", "on")
        monkeypatch.setenv("BOOKING_PHASE2_GYM_LOCATION_V2", "True")

        assert is_phase2_availability_enabled() is True
        assert is_phase2_travel_buffer_enabled() is True
        assert is_phase2_multi_set_boat_enabled() is True
        assert is_phase2_summary_v2_enabled() is True
        assert is_phase2_gym_location_v2_enabled() is True

    def test_travel_buffer_requires_availability(self, monkeypatch):
        monkeypatch.delenv("BOOKING_PHASE2_AVAILABILITY", raising=False)
        monkeypatch.setenv("BOOKING_PHASE2_TRAVEL_BUFFER", "1")
        assert is_phase2_availability_enabled() is False
        assert is_phase2_travel_buffer_enabled() is False

        monkeypatch.setenv("BOOKING_PHASE2_AVAILABILITY", "1")
        assert is_phase2_travel_buffer_enabled() is True


class TestCapacityCanon:
    def test_boat_exclusive_capacity(self):
        assert BOAT_MAX_CLIENTS_PER_SLOT == 1

    def test_gym_group_capacity(self):
        assert GYM_MAX_CLIENTS_PER_SLOT == 4

    def test_duration_constants(self):
        assert BOAT_SET_MINUTES == 30
        assert GYM_SLOT_MINUTES == 90
        assert TRAINER_TRAVEL_BUFFER_MINUTES == 120
        assert BOOKING_DURATION_MINUTES["boat"] == BOAT_SET_MINUTES
        assert BOOKING_DURATION_MINUTES["gym"] == GYM_SLOT_MINUTES


class TestBookingVenues:
    def test_gym_venue_v2_location(self):
        assert GYM_VENUE["calendar_location_v2"] == "Зал"
        assert GYM_VENUE["latitude"] == pytest.approx(55.777052)
        assert GYM_VENUE["longitude"] == pytest.approx(37.502594)
        assert "yandex.ru/maps" in GYM_VENUE["yandex_maps_url"]

    def test_boat_venue_uses_phase1_calendar_location(self):
        assert "MyWave Wake" in BOAT_VENUE["calendar_location"]
        assert "yandex.ru/maps" in BOAT_VENUE["yandex_maps_url"]

    def test_booking_venues_registry(self):
        assert set(BOOKING_VENUES) == {"gym", "boat"}
