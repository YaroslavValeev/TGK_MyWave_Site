"""Sheets journal cancel for yc-{record_id}."""

from unittest.mock import MagicMock, patch


def test_mark_yclients_journal_cancelled(app):
    with app.app_context():
        app.config["SPREADSHEET_ID"] = "sheet-test"
        workout_sheet = MagicMock()
        workout_sheet.values = [
            ["workout_id", "workout_status", "current_capacity"],
            ["yc-123", "active", "1"],
        ]
        workout_sheet.find_rows.return_value = [(2, {"workout_id": "yc-123"})]

        cw_sheet = MagicMock()
        cw_sheet.values = [["id", "workout_id", "status"], ["cw1", "yc-123", "подтверждено"]]
        cw_sheet.find_rows.return_value = [(2, {"workout_id": "yc-123"})]

        def get_sheet(name):
            return workout_sheet if name == "Workouts" else cw_sheet

        with (
            patch(
                "app.modules.sheets_access.get_google_sheet",
                side_effect=get_sheet,
            ),
            patch(
                "app.services.google_sheets_service.update_record"
            ) as mock_update,
        ):
            from app.services.booking.sheets_writer import mark_yclients_journal_cancelled

            result = mark_yclients_journal_cancelled("123")

        assert result["workout_id"] == "yc-123"
        assert result["workouts"] is True
        assert result["client_workouts"] == 1
        assert mock_update.call_count >= 2
