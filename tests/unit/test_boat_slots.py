"""Слоты катера: 1 ученик на сет, занятые не возвращаются."""
from unittest.mock import patch

import pytest

from app.routes.calendar_routes import get_boat_slots, BOAT_MAX_PER_SLOT


@pytest.mark.parametrize("used_at_time,expect_time_present", [
    (0, True),
    (1, False),
    (2, False),
])
def test_boat_slots_hide_full(app, used_at_time, expect_time_present):
  bookings = []
  for _ in range(used_at_time):
    bookings.append({
      "date": "2026-06-12",
      "time": "09:00",
      "service_type": "boat",
      "status": "booked",
    })

  with app.app_context():
    app.config["SPREADSHEET_ID"] = "test-sheet"
    with patch("app.routes.calendar_routes.read_records", return_value=bookings):
      slots = get_boat_slots("2026-06-12")

  times = [s["time"] for s in slots]
  assert ("09:00" in times) is expect_time_present
  assert all(s.get("available") is True for s in slots)
  assert BOAT_MAX_PER_SLOT == 1


def test_boat_slots_grid_boundaries(app):
    """Legacy Phase 1 path: starts 07:00–19:30, no 06:00 or 20:00+ starts."""
    with app.app_context():
        app.config["SPREADSHEET_ID"] = "test-sheet"
        with patch("app.routes.calendar_routes.read_records", return_value=[]):
            slots = get_boat_slots("2026-06-12")

    times = [s["time"] for s in slots]
    assert "06:00" not in times
    assert "06:30" not in times
    assert "07:00" in times
    assert "19:30" in times
    assert "20:00" not in times
    assert "21:00" not in times
    assert times[0] == "07:00"
    assert times[-1] == "19:30"
