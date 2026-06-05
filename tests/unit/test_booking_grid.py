"""Canonical boat grid hours (Owner: sync Site with TGbotAdmin)."""

from datetime import time

from app.config.booking_grid import BOAT_GRID_END, BOAT_GRID_START


def test_boat_grid_canonical():
    assert BOAT_GRID_START == time(7, 0)
    assert BOAT_GRID_END == time(19, 30)


def test_availability_imports_grid_constants():
    from app.services.booking import availability

    assert availability.BOAT_GRID_START == time(7, 0)
    assert availability.BOAT_GRID_END == time(19, 30)
