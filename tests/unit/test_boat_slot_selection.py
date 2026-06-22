"""Tests for boat multi-slot selection normalization (PR53.1)."""

import pytest

from app.services.booking.boat_slot_selection import (
    are_consecutive_boat_slots,
    normalize_boat_slot_booking,
)


def test_single_slot():
    assert normalize_boat_slot_booking(["10:00"]) == ("10:00", 1)


def test_consecutive_slots():
    assert normalize_boat_slot_booking(["10:00", "10:30", "11:00"]) == (
        "10:00",
        3,
    )


def test_non_consecutive_slots():
    assert normalize_boat_slot_booking(["10:00", "11:00"]) == ["10:00", "11:00"]


def test_are_consecutive_boat_slots():
    assert are_consecutive_boat_slots(["10:00", "10:30"]) is True
    assert are_consecutive_boat_slots(["10:00", "11:00"]) is False


def test_empty_raises():
    with pytest.raises(ValueError):
        normalize_boat_slot_booking([])
