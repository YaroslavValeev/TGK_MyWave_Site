"""Partial Sheets failure — compensating delete (Option B)."""

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest

from app.services.booking.pipeline import (
    CalendarBookingError,
    SheetsBookingError,
    execute_web_booking,
)
from app.services.booking.sheets_writer import WORKOUT_STATUS_CANCELLED


def _enter_pipeline_patches(stack: ExitStack, event_id="evt_cal_99"):
    stack.enter_context(
        patch(
            "app.services.booking.pipeline.is_duplicate_web_booking",
            return_value=False,
        )
    )
    stack.enter_context(
        patch(
            "app.services.booking.pipeline.generate_booking_id",
            return_value="bk_comp001",
        )
    )
    stack.enter_context(
        patch(
            "app.services.booking.pipeline.resolve_client",
            return_value=MagicMock(client_id="client_1", created=True),
        )
    )
    return stack.enter_context(
        patch(
            "app.services.booking.pipeline.create_calendar_event",
            return_value=event_id,
        )
    )


class TestPartialSheetsCompensation:
    def test_client_workout_fail_compensates_workout_and_calendar(self, app):
        with app.app_context():
            app.config["SPREADSHEET_ID"] = "test-sheet"
            app.config["GOOGLE_CALENDAR_ID"] = "cal@test"
            with ExitStack() as stack:
                _enter_pipeline_patches(stack)
                mock_w = stack.enter_context(
                    patch("app.services.booking.pipeline.write_workout_row")
                )
                stack.enter_context(
                    patch(
                        "app.services.booking.pipeline.write_client_workout_row",
                        side_effect=RuntimeError("sheets append failed"),
                    )
                )
                mock_comp = stack.enter_context(
                    patch(
                        "app.services.booking.pipeline.compensate_workout_row",
                        return_value=True,
                    )
                )
                mock_del = stack.enter_context(
                    patch(
                        "app.services.booking.pipeline.delete_calendar_event_best_effort",
                        return_value=True,
                    )
                )
                with pytest.raises(SheetsBookingError):
                    execute_web_booking(
                        date="2026-06-01",
                        time="12:00",
                        name="Иван",
                        phone="+79160117179",
                        service_type="gym",
                    )
                mock_w.assert_called_once()
                mock_comp.assert_called_once_with("evt_cal_99")
                mock_del.assert_called_once_with("evt_cal_99")

    def test_calendar_fail_still_no_sheets(self, app):
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
                patch(
                    "app.services.booking.pipeline.compensate_workout_row"
                ) as mock_comp,
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
                mock_comp.assert_not_called()

    def test_success_no_compensation(self, app):
        with app.app_context():
            with ExitStack() as stack:
                _enter_pipeline_patches(stack)
                stack.enter_context(
                    patch("app.services.booking.pipeline.write_workout_row")
                )
                stack.enter_context(
                    patch(
                        "app.services.booking.pipeline.write_client_workout_row",
                        return_value="cw_ok",
                    )
                )
                mock_comp = stack.enter_context(
                    patch("app.services.booking.pipeline.compensate_workout_row")
                )
                mock_del = stack.enter_context(
                    patch(
                        "app.services.booking.pipeline.delete_calendar_event_best_effort"
                    )
                )
                result = execute_web_booking(
                    date="2026-06-01",
                    time="12:00",
                    name="Иван",
                    phone="+79160117179",
                    service_type="boat",
                )
                assert result.workout_id == "evt_cal_99"
                mock_comp.assert_not_called()
                mock_del.assert_not_called()


class TestCompensateWorkoutRow:
    def test_marks_workout_status_cancelled(self, app):
        with app.app_context():
            app.config["SPREADSHEET_ID"] = "test-sheet"
            mock_sheet = MagicMock()
            mock_sheet.values = [
                [
                    "workout_id",
                    "date",
                    "time",
                    "duration",
                    "location",
                    "workout_type",
                    "max_capacity",
                    "coach_name",
                    "workout_status",
                    "current_capacity",
                ],
                ["evt_1", "2026-06-01", "12:00", "90", "Зал", "gym", "", "", "active", "1"],
            ]
            mock_sheet.find_rows.return_value = [(2, {"workout_id": "evt_1"})]

            with (
                patch(
                    "app.modules.sheets_access.get_google_sheet",
                    return_value=mock_sheet,
                ),
                patch(
                    "app.services.google_sheets_service.update_record"
                ) as mock_update,
            ):
                from app.services.booking.sheets_writer import compensate_workout_row

                ok = compensate_workout_row("evt_1")
                assert ok is True
                assert mock_update.call_count == 2
                status_call = mock_update.call_args_list[0]
                assert status_call[0][2] == "I2"
                assert status_call[0][3] == [WORKOUT_STATUS_CANCELLED]
