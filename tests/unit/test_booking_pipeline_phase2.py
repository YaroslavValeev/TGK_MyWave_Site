"""Phase 2 POST pipeline: recheck, 409 path, idempotency range, flags OFF regression."""

from datetime import datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from app.services.booking.availability import (
    SlotUnavailableError,
    assert_booking_available,
)
from app.services.booking.calendar_reader import BusyInterval
from app.services.booking.idempotency import is_duplicate_web_booking
from app.services.booking.pipeline import (
    CalendarBookingError,
    DuplicateBookingError,
    execute_web_booking,
)

TZ = ZoneInfo("Europe/Moscow")


def _dt(h, m=0):
    return datetime(2026, 6, 15, h, m, tzinfo=TZ)


def _iv(h1, m1, h2, m2, st):
    return BusyInterval(_dt(h1, m1), _dt(h2, m2), st)


class TestAssertBookingAvailable:
    def test_assert_booking_boat_blocked(self, app):
        intervals = [_iv(18, 0, 18, 30, "boat")]
        with app.app_context():
            with patch(
                "app.services.booking.availability.list_busy_intervals_for_date",
                return_value=intervals,
            ):
                with pytest.raises(SlotUnavailableError):
                    assert_booking_available("2026-06-15", "18:00", "boat", set_count=1)

    def test_assert_booking_gym_4_of_4(self, app):
        intervals = [
            _iv(10, 0, 11, 30, "gym"),
            _iv(10, 0, 11, 30, "gym"),
            _iv(10, 0, 11, 30, "gym"),
            _iv(10, 0, 11, 30, "gym"),
        ]
        with app.app_context():
            with patch(
                "app.services.booking.availability.list_busy_intervals_for_date",
                return_value=intervals,
            ):
                with pytest.raises(SlotUnavailableError) as exc:
                    assert_booking_available("2026-06-15", "10:00", "gym")
                assert str(exc.value) == "gym_capacity_full"

    def test_assert_booking_gym_3_of_4_allows(self, app):
        intervals = [
            _iv(10, 0, 11, 30, "gym"),
            _iv(10, 0, 11, 30, "gym"),
            _iv(10, 0, 11, 30, "gym"),
        ]
        with app.app_context():
            with patch(
                "app.services.booking.availability.list_busy_intervals_for_date",
                return_value=intervals,
            ):
                assert_booking_available("2026-06-15", "10:00", "gym")

    def test_assert_booking_travel_buffer_blocks(self, app):
        intervals = [_iv(8, 0, 9, 30, "gym")]
        with app.app_context():
            with (
                patch(
                    "app.services.booking.availability.list_busy_intervals_for_date",
                    return_value=intervals,
                ),
                patch(
                    "app.services.booking.availability.is_phase2_travel_buffer_enabled",
                    return_value=True,
                ),
            ):
                with pytest.raises(SlotUnavailableError):
                    # gym ends 09:30 + 120 min buffer → boat from 11:30; 11:00 still inside buffer
                    assert_booking_available("2026-06-15", "11:00", "boat", set_count=1)


class TestPipelineRecheck:
    def test_recheck_blocks_no_calendar_no_sheets(self, app):
        with app.app_context():
            app.config["SPREADSHEET_ID"] = "x"
            app.config["GOOGLE_CALENDAR_ID"] = "cal@test"
            with (
                patch(
                    "app.services.booking.pipeline.is_phase2_availability_enabled",
                    return_value=True,
                ),
                patch(
                    "app.services.booking.pipeline.is_duplicate_web_booking",
                    return_value=False,
                ),
                patch(
                    "app.services.booking.pipeline.assert_booking_available",
                    side_effect=SlotUnavailableError("boat_slot_occupied"),
                ),
                patch(
                    "app.services.booking.pipeline.resolve_client",
                ) as mock_client,
                patch(
                    "app.services.booking.pipeline.create_calendar_event",
                ) as mock_cal,
                patch("app.services.booking.pipeline.write_workout_row") as mock_w,
                patch(
                    "app.services.booking.pipeline.write_client_workout_row"
                ) as mock_cw,
            ):
                with pytest.raises(SlotUnavailableError):
                    execute_web_booking(
                        date="2026-06-15",
                        time="18:00",
                        name="Иван",
                        phone="+79160117179",
                        service_type="boat",
                        set_count=1,
                    )
                mock_client.assert_not_called()
                mock_cal.assert_not_called()
                mock_w.assert_not_called()
                mock_cw.assert_not_called()

    def test_calendar_failure_no_sheets(self, app):
        with app.app_context():
            with (
                patch(
                    "app.services.booking.pipeline.is_duplicate_web_booking",
                    return_value=False,
                ),
                patch(
                    "app.services.booking.pipeline.generate_booking_id",
                    return_value="bk_x",
                ),
                patch(
                    "app.services.booking.pipeline.resolve_client",
                    return_value=MagicMock(client_id="c1"),
                ),
                patch(
                    "app.services.booking.pipeline.create_calendar_event",
                    side_effect=RuntimeError("calendar down"),
                ),
                patch("app.services.booking.pipeline.write_workout_row") as mock_w,
                patch(
                    "app.services.booking.pipeline.write_client_workout_row"
                ) as mock_cw,
            ):
                with pytest.raises(CalendarBookingError):
                    execute_web_booking(
                        date="2026-06-01",
                        time="12:00",
                        name="Иван",
                        phone="+79160117179",
                    )
                mock_w.assert_not_called()
                mock_cw.assert_not_called()


class TestPipelineFlagsOff:
    def test_flags_off_skips_recheck(self, app):
        with app.app_context():
            app.config["SPREADSHEET_ID"] = "x"
            app.config["GOOGLE_CALENDAR_ID"] = "cal@test"
            with (
                patch(
                    "app.services.booking.pipeline.is_phase2_availability_enabled",
                    return_value=False,
                ),
                patch(
                    "app.services.booking.pipeline.is_duplicate_web_booking",
                    return_value=False,
                ),
                patch(
                    "app.services.booking.pipeline.assert_booking_available",
                ) as mock_assert,
                patch(
                    "app.services.booking.pipeline.generate_booking_id",
                    return_value="bk_1",
                ),
                patch(
                    "app.services.booking.pipeline.resolve_client",
                    return_value=MagicMock(client_id="c1"),
                ),
                patch(
                    "app.services.booking.pipeline.create_calendar_event",
                    return_value="evt_1",
                ) as mock_cal,
                patch("app.services.booking.pipeline.write_workout_row"),
                patch(
                    "app.services.booking.pipeline.write_client_workout_row",
                    return_value="cw_1",
                ),
            ):
                execute_web_booking(
                    date="2026-06-01",
                    time="12:00",
                    name="Иван",
                    phone="+79160117179",
                    service_type="boat",
                    set_count=3,
                )
                mock_assert.assert_not_called()
                assert mock_cal.call_args.kwargs["set_count"] == 1

    def test_workout_id_equals_event_id(self, app):
        with app.app_context():
            app.config["SPREADSHEET_ID"] = "x"
            with (
                patch(
                    "app.services.booking.pipeline.is_duplicate_web_booking",
                    return_value=False,
                ),
                patch(
                    "app.services.booking.pipeline.generate_booking_id",
                    return_value="bk_1",
                ),
                patch(
                    "app.services.booking.pipeline.resolve_client",
                    return_value=MagicMock(client_id="c1"),
                ),
                patch(
                    "app.services.booking.pipeline.create_calendar_event",
                    return_value="google_evt_99",
                ),
                patch("app.services.booking.pipeline.write_workout_row"),
                patch(
                    "app.services.booking.pipeline.write_client_workout_row",
                    return_value="cw_1",
                ),
            ):
                result = execute_web_booking(
                    date="2026-06-01",
                    time="12:00",
                    name="Иван",
                    phone="+79160117179",
                )
                assert result.workout_id == "google_evt_99"


class TestIdempotencyRange:
    def test_idempotency_range_same_end_dup(self, app):
        with app.app_context():
            app.config["SPREADSHEET_ID"] = "test-sheet"
            with (
                patch(
                    "app.services.booking.idempotency.is_phase2_availability_enabled",
                    return_value=True,
                ),
                patch(
                    "app.services.booking.idempotency.read_records",
                    side_effect=[
                        [{"client_id": "c1", "phone": "+79160117179"}],
                        [
                            {
                                "client_id": "c1",
                                "workout_id": "evt_old",
                                "date": "2026-06-15",
                                "time": "18:00",
                                "status": "подтверждено",
                            }
                        ],
                        [
                            {
                                "workout_id": "evt_old",
                                "workout_type": "boat",
                                "duration": "90",
                            }
                        ],
                    ],
                ),
            ):
                assert is_duplicate_web_booking(
                    "+79160117179",
                    "2026-06-15",
                    "18:00",
                    "boat",
                    set_count=3,
                )

    def test_idempotency_different_set_count_not_dup(self, app):
        with app.app_context():
            app.config["SPREADSHEET_ID"] = "test-sheet"
            with (
                patch(
                    "app.services.booking.idempotency.is_phase2_availability_enabled",
                    return_value=True,
                ),
                patch(
                    "app.services.booking.idempotency.read_records",
                    side_effect=[
                        [{"client_id": "c1", "phone": "+79160117179"}],
                        [
                            {
                                "client_id": "c1",
                                "workout_id": "evt_old",
                                "date": "2026-06-15",
                                "time": "18:00",
                                "status": "подтверждено",
                            }
                        ],
                        [
                            {
                                "workout_id": "evt_old",
                                "workout_type": "boat",
                                "duration": "30",
                            }
                        ],
                    ],
                ),
            ):
                assert not is_duplicate_web_booking(
                    "+79160117179",
                    "2026-06-15",
                    "18:00",
                    "boat",
                    set_count=3,
                )


class TestDuplicateRaises:
    def test_duplicate_raises(self, app):
        with app.app_context():
            with patch(
                "app.services.booking.pipeline.is_duplicate_web_booking",
                return_value=True,
            ):
                with pytest.raises(DuplicateBookingError):
                    execute_web_booking(
                        date="2026-06-01",
                        time="12:00",
                        name="Иван",
                        phone="+79160117179",
                        service_type="gym",
                    )
