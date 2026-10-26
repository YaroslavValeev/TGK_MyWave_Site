"""Phase 1 booking pipeline unit tests (Calendar-first, contract v1.0)."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.booking import pipeline
from app.services.booking.calendar_writer import build_event_summary
from app.services.booking.client_resolver import resolve_client
from app.services.booking.constants import SHEETS_STATUS_CONFIRMED
from app.services.booking.idempotency import is_duplicate_web_booking
from app.services.booking.phone import normalize_phone
from app.services.booking.pipeline import (
    CalendarBookingError,
    DuplicateBookingError,
    execute_web_booking,
)


@pytest.mark.parametrize(
    "mode,provider,service",
    [
        ("1", "calendar", "boat"),
        ("true", "yclients", "boat"),
        ("YES", "calendar", "gym"),
        ("on", "calendar", "boat"),
        ("0", "site_internal", "boat"),
        ("0", " SITE_INTERNAL ", "boat"),
    ],
)
def test_unwired_internal_mode_stops_before_external_io(
    monkeypatch, mode, provider, service
):
    monkeypatch.setenv("CLUB_BOX_MODE", mode)
    monkeypatch.setenv("BOAT_PROVIDER", provider)
    calls = []
    for name in (
        "is_duplicate_web_booking",
        "resolve_client",
        "assert_booking_available",
        "create_calendar_event",
        "write_workout_row",
        "write_client_workout_row",
        "_execute_boat_yclients_booking",
    ):
        call = MagicMock(side_effect=AssertionError("external IO must not run"))
        monkeypatch.setattr(pipeline, name, call)
        calls.append(call)

    with pytest.raises(
        pipeline.CalendarBookingError, match="club_box_web_writer_not_configured"
    ):
        pipeline.execute_web_booking(
            date="2027-06-01",
            time="10:00",
            name="Synthetic",
            phone="79990000001",
            service_type=service,
        )
    for call in calls:
        call.assert_not_called()


def test_legacy_calendar_writer_still_works_when_internal_mode_is_off(monkeypatch):
    monkeypatch.setenv("CLUB_BOX_MODE", "0")
    monkeypatch.setenv("BOAT_PROVIDER", "calendar")
    monkeypatch.setattr(pipeline, "is_phase2_availability_enabled", lambda: False)
    monkeypatch.setattr(pipeline, "is_duplicate_web_booking", lambda *a, **k: False)
    monkeypatch.setattr(pipeline, "generate_booking_id", lambda: "web-intent-1")
    monkeypatch.setattr(
        pipeline, "resolve_client", lambda *a: MagicMock(client_id="client-1")
    )
    calendar = MagicMock(return_value="calendar-record-1")
    journal = MagicMock(return_value="journal-1")
    monkeypatch.setattr(pipeline, "create_calendar_event", calendar)
    monkeypatch.setattr(pipeline, "_write_sheets_journal", journal)

    result = pipeline.execute_web_booking(
        date="2027-06-01",
        time="10:00",
        name="Synthetic",
        phone="79990000001",
        service_type="boat",
    )
    assert result.workout_id == "calendar-record-1"
    assert result.booking_id == "web-intent-1"
    assert result.client_workout_id == "journal-1"
    calendar.assert_called_once()
    journal.assert_called_once()


class TestPhone:
    def test_normalize_8_prefix(self):
        assert normalize_phone("89160117179") == "+79160117179"

    def test_normalize_plus7(self):
        assert normalize_phone("+79160117179") == "+79160117179"


class TestSummary:
    def test_telegram_summary_uses_id_marker(self):
        s = build_event_summary("boat", "Иван", telegram_user_id="123456789")
        assert "(ID: 123456789)" in s
        assert "WEB_ID" not in s
        assert "Тренировка (Катер)" in s

    def test_web_summary_uses_web_id_marker(self):
        s = build_event_summary("boat", "Иван", booking_id="bk_abc123")
        assert "(WEB_ID: bk_abc123)" in s
        assert "(ID:" not in s


class TestIdempotency:
    def test_duplicate_detected(self, app):
        with app.app_context():
            app.config["SPREADSHEET_ID"] = "test-sheet"
            with patch(
                "app.services.booking.idempotency.read_records",
                side_effect=[
                    [{"client_id": "c1", "phone": "+79160117179"}],
                    [
                        {
                            "client_id": "c1",
                            "workout_id": "evt_old",
                            "date": "2026-06-01",
                            "time": "12:00",
                            "status": "подтверждено",
                        }
                    ],
                    [{"workout_id": "evt_old", "workout_type": "gym"}],
                ],
            ):
                assert is_duplicate_web_booking(
                    "+79160117179", "2026-06-01", "12:00", "gym"
                )

    def test_duplicate_skips_non_numeric_workout_duration(self, app):
        """Prod Workouts rows may have text in duration (e.g. 'Зал'); must not 500."""
        with app.app_context():
            app.config["SPREADSHEET_ID"] = "test-sheet"
            with patch(
                "app.services.booking.idempotency.read_records",
                side_effect=[
                    [{"client_id": "c1", "phone": "+79160117179"}],
                    [
                        {
                            "client_id": "c1",
                            "workout_id": "evt_old",
                            "date": "2026-06-01",
                            "time": "12:00",
                            "status": "подтверждено",
                        }
                    ],
                    [
                        {
                            "workout_id": "evt_old",
                            "workout_type": "gym",
                            "duration": "Зал",
                        },
                        {
                            "workout_id": "evt_other",
                            "workout_type": "boat",
                            "duration": "60",
                        },
                    ],
                ],
            ):
                assert is_duplicate_web_booking(
                    "+79160117179", "2026-06-01", "12:00", "gym"
                )


class TestClientResolver:
    def test_reuse_existing_client_by_phone(self, app):
        with app.app_context():
            app.config["SPREADSHEET_ID"] = "test-sheet"
            with (
                patch(
                    "app.services.booking.client_resolver._read_clients",
                    return_value=[
                        {
                            "client_id": "client_existing",
                            "phone": "+79160117179",
                            "telegram_user_id": "999",
                        }
                    ],
                ),
                patch("app.modules.sheets_access.append_dict_to_sheet") as mock_append,
            ):
                result = resolve_client("89160117179", "Иван")
                assert result.client_id == "client_existing"
                assert result.matched_by == "phone"
                assert not result.created
                mock_append.assert_not_called()

    def test_web_booking_does_not_overwrite_telegram_user_id(self, app):
        """Reuse by phone only — no Sheets update in Phase 1."""
        with app.app_context():
            app.config["SPREADSHEET_ID"] = "test-sheet"
            existing = {
                "client_id": "client_existing",
                "phone": "+79160117179",
                "telegram_user_id": "888777666",
            }
            with (
                patch(
                    "app.services.booking.client_resolver._read_clients",
                    return_value=[existing],
                ),
                patch("app.modules.sheets_access.append_dict_to_sheet") as mock_append,
            ):
                result = resolve_client("+79160117179", "Web User")
                assert result.client_id == "client_existing"
                mock_append.assert_not_called()
                assert existing["telegram_user_id"] == "888777666"

    def test_create_new_web_client(self, app):
        with app.app_context():
            app.config["SPREADSHEET_ID"] = "test-sheet"
            with (
                patch(
                    "app.services.booking.client_resolver._read_clients",
                    return_value=[],
                ),
                patch("app.modules.sheets_access.append_dict_to_sheet") as mock_append,
            ):
                result = resolve_client("+79160001122", "Пётр")
                assert result.created
                assert result.client_id.startswith("client_")
                mock_append.assert_called_once()
                row = mock_append.call_args[0][1]
                assert row["telegram_user_id"] == ""
                assert row["source"] == "web"


class TestPipeline:
    def _patch_pipeline_deps(self, event_id="evt_cal_123"):
        return patch.multiple(
            "app.services.booking.pipeline",
            is_duplicate_web_booking=MagicMock(return_value=False),
            generate_booking_id=MagicMock(return_value="bk_test001"),
            resolve_client=MagicMock(
                return_value=MagicMock(
                    client_id="client_1", created=True, matched_by="new"
                )
            ),
            create_calendar_event=MagicMock(return_value=event_id),
            write_workout_row=MagicMock(),
            write_client_workout_row=MagicMock(return_value="cw_1"),
        )

    def test_web_booking_creates_calendar_then_sheets(self, app):
        with app.app_context():
            app.config["SPREADSHEET_ID"] = "x"
            app.config["GOOGLE_CALENDAR_ID"] = "cal@group.calendar.google.com"
            with (
                patch(
                    "app.services.booking.pipeline.is_duplicate_web_booking",
                    return_value=False,
                ),
                patch(
                    "app.services.booking.pipeline.generate_booking_id",
                    return_value="bk_test001",
                ),
                patch(
                    "app.services.booking.pipeline.resolve_client",
                    return_value=MagicMock(
                        client_id="client_1", created=True, matched_by="new"
                    ),
                ),
                patch(
                    "app.services.booking.pipeline.create_calendar_event",
                    return_value="evt_cal_123",
                ) as mock_cal,
                patch(
                    "app.services.booking.pipeline.write_workout_row",
                ) as mock_w,
                patch(
                    "app.services.booking.pipeline.write_client_workout_row",
                    return_value="cw_1",
                ) as mock_cw,
            ):
                result = execute_web_booking(
                    date="2026-06-01",
                    time="12:00",
                    name="Иван",
                    phone="+79160117179",
                    service_type="boat",
                )
                assert result.workout_id == "evt_cal_123"
                mock_cal.assert_called_once()
                mock_w.assert_called_once()
                mock_cw.assert_called_once()
                assert mock_w.call_args.kwargs["workout_id"] == "evt_cal_123"

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


class TestPathB:
    def test_sheets_book_slot_uses_pipeline(self, app):
        with app.app_context():
            with patch(
                "app.services.booking.execute_web_booking",
                return_value=MagicMock(workout_id="evt_1"),
            ) as mock_exec:
                from app.modules.sheets import book_slot

                ok, msg = book_slot("2026-06-01", "12:00", "Test", "+79160117179")
                assert ok is True
                mock_exec.assert_called_once()


class TestSheetsStatus:
    def test_confirmed_status_constant(self):
        assert SHEETS_STATUS_CONFIRMED == "подтверждено"


class TestLoggingNoPii:
    def test_pipeline_logs_no_raw_phone(self, app, caplog):
        import logging

        caplog.set_level(logging.INFO)
        with app.app_context():
            app.config["SPREADSHEET_ID"] = "x"
            app.config["GOOGLE_CALENDAR_ID"] = "cal@group.calendar.google.com"
            phone = "+79160117179"
            with (
                patch(
                    "app.services.booking.pipeline.is_duplicate_web_booking",
                    return_value=False,
                ),
                patch(
                    "app.services.booking.pipeline.generate_booking_id",
                    return_value="bk_test001",
                ),
                patch(
                    "app.services.booking.pipeline.resolve_client",
                    return_value=MagicMock(
                        client_id="client_1", created=True, matched_by="new"
                    ),
                ),
                patch(
                    "app.services.booking.pipeline.create_calendar_event",
                    return_value="evt_cal_123",
                ),
                patch(
                    "app.services.booking.pipeline.write_workout_row",
                ),
                patch(
                    "app.services.booking.pipeline.write_client_workout_row",
                    return_value="cw_1",
                ),
            ):
                execute_web_booking(
                    date="2026-06-01",
                    time="12:00",
                    name="Иван",
                    phone=phone,
                    service_type="boat",
                )
        combined = caplog.text + " ".join(r.message for r in caplog.records)
        assert phone not in combined
        assert "9160117179" not in combined
