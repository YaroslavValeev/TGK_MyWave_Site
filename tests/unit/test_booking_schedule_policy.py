"""Unit tests for seasonal gym schedule policy."""

from __future__ import annotations

from datetime import date

import pytest

from app.services.booking.schedule_policy import (
    GYM_SEASONAL_ERROR_CODE,
    GymSeasonalRestrictionError,
    apply_gym_seasonal_slot_rows,
    assert_gym_slot_allowed,
    filter_gym_slots,
    get_gym_available_slots,
    is_gym_slot_allowed,
    is_seasonal_rules_active,
)


@pytest.fixture(autouse=True)
def enable_seasonal_rules(monkeypatch):
    monkeypatch.setenv("BOOKING_SEASONAL_RULES_ENABLED", "1")
    monkeypatch.setenv("BOOKING_SEASONAL_RULES_UNTIL", "2026-09-30")
    monkeypatch.setenv("GYM_SEASONAL_WEEKDAYS", "0,3")
    monkeypatch.setenv("GYM_SEASONAL_START_TIME", "19:00")


def test_seasonal_active_until_cutoff():
    assert is_seasonal_rules_active("2026-09-30") is True
    assert is_seasonal_rules_active("2026-10-01") is False


def test_monday_1900_allowed():
    # 2026-07-13 is Monday
    assert is_gym_slot_allowed("2026-07-13", "19:00") is True
    assert_gym_slot_allowed("2026-07-13", "19:00")


def test_thursday_1900_allowed():
    # 2026-07-16 is Thursday
    assert is_gym_slot_allowed("2026-07-16", "19:00") is True


def test_tuesday_denied():
    assert is_gym_slot_allowed("2026-07-14", "19:00") is False
    with pytest.raises(GymSeasonalRestrictionError) as exc:
        assert_gym_slot_allowed("2026-07-14", "19:00")
    assert exc.value.code == GYM_SEASONAL_ERROR_CODE


def test_monday_wrong_time_denied():
    assert is_gym_slot_allowed("2026-07-13", "10:00") is False


def test_apply_slot_rows_monday_only_1900():
    rows = apply_gym_seasonal_slot_rows(
        "2026-07-13",
        [{"time": "10:00", "max_capacity": 4}, {"time": "19:00", "max_capacity": 4}],
    )
    assert len(rows) == 1
    assert rows[0]["time"] == "19:00"


def test_apply_slot_rows_tuesday_empty():
    rows = apply_gym_seasonal_slot_rows("2026-07-14", [{"time": "19:00", "max_capacity": 4}])
    assert rows == []


def test_filter_gym_slots_injects_monday_slot():
    slots = filter_gym_slots("2026-07-13", [])
    assert len(slots) == 1
    assert slots[0]["time"] == "19:00"


def test_get_gym_available_slots_wrapper():
    base = [{"time": "10:00", "available": True}, {"time": "19:00", "available": True}]
    out = get_gym_available_slots("2026-07-13", base)
    assert len(out) == 1
    assert out[0]["time"] == "19:00"


def test_after_october_uses_base_schedule(monkeypatch):
    monkeypatch.setenv("BOOKING_SEASONAL_RULES_UNTIL", "2026-09-30")
    base = [{"time": "10:00", "available": True}, {"time": "15:00", "available": True}]
    out = get_gym_available_slots("2026-10-05", base)
    assert out == base


def test_seasonal_disabled_passes_through(monkeypatch):
    monkeypatch.setenv("BOOKING_SEASONAL_RULES_ENABLED", "0")
    base = [{"time": "10:00", "available": True}]
    assert get_gym_available_slots("2026-07-14", base) == base
