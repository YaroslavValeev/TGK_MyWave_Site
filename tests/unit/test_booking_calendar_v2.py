"""Phase 2 Calendar writer v2 (summary, duration, extendedProperties)."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app.services.booking.calendar_writer import (
    booking_duration_minutes,
    build_calendar_event_body,
    build_event_summary,
    build_event_summary_v2,
    format_boat_sets_label,
    get_calendar_location,
    resolve_event_summary,
)


class TestFormatBoatSets:
    def test_one_set(self):
        assert format_boat_sets_label(1) == "1 сет"

    def test_three_sets(self):
        assert format_boat_sets_label(3) == "3 сета"

    def test_five_sets(self):
        assert format_boat_sets_label(5) == "5 сетов"


class TestSummaryV2:
    def test_summary_v2_gym(self):
        s = build_event_summary_v2("gym", "Иван", booking_id="bk_abc")
        assert s == "Тренировка — Зал — Иван (WEB_ID: bk_abc)"

    def test_summary_v2_boat_3_sets(self):
        s = build_event_summary_v2("boat", "Иван", set_count=3, booking_id="bk_x")
        assert "3 сета" in s
        assert "Катер" in s
        assert "(WEB_ID: bk_x)" in s

    def test_telegram_unchanged_v1(self):
        s = build_event_summary("boat", "Иван", telegram_user_id="123456789")
        assert "(ID: 123456789)" in s
        assert "WEB_ID" not in s

    def test_web_id_not_telegram_id(self):
        s = build_event_summary_v2("gym", "Иван", booking_id="bk_web1")
        assert "(WEB_ID:" in s
        assert "(ID:" not in s


class TestWriterFlags:
    def test_summary_v1_when_flag_off(self, app):
        with app.app_context():
            with patch(
                "app.services.booking.calendar_writer.is_phase2_summary_v2_enabled",
                return_value=False,
            ):
                s = resolve_event_summary("boat", "Иван", booking_id="bk_1")
                assert "Тренировка (Катер)" in s

    def test_summary_v2_when_flag_on(self, app):
        with app.app_context():
            with patch(
                "app.services.booking.calendar_writer.is_phase2_summary_v2_enabled",
                return_value=True,
            ):
                s = resolve_event_summary(
                    "boat", "Иван", set_count=2, booking_id="bk_2"
                )
                assert "2 сета" in s
                assert "—" in s

    def test_gym_location_v2(self, app):
        with app.app_context():
            with patch(
                "app.services.booking.calendar_writer.is_phase2_gym_location_v2_enabled",
                return_value=True,
            ):
                assert get_calendar_location("gym") == "Зал"

    def test_gym_location_v1(self, app):
        with app.app_context():
            with patch(
                "app.services.booking.calendar_writer.is_phase2_gym_location_v2_enabled",
                return_value=False,
            ):
                assert get_calendar_location("gym") == "Зал MyWave"


class TestEventBody:
    def test_boat_duration_3_sets(self, app):
        with app.app_context():
            app.config["TIMEZONE"] = "Europe/Moscow"
            with patch(
                "app.services.booking.calendar_writer.is_phase2_availability_enabled",
                return_value=True,
            ):
                body = build_calendar_event_body(
                    date="2026-06-15",
                    time="18:00",
                    name="Иван",
                    phone="+79160001122",
                    service_type="boat",
                    booking_id="bk_test",
                    client_id="client_1",
                    set_count=3,
                )
                start = datetime.fromisoformat(body["start"]["dateTime"])
                end = datetime.fromisoformat(body["end"]["dateTime"])
                assert (end - start) == timedelta(minutes=90)

    def test_extended_properties_set_count(self, app):
        with app.app_context():
            app.config["TIMEZONE"] = "Europe/Moscow"
            with patch(
                "app.services.booking.calendar_writer.is_phase2_availability_enabled",
                return_value=True,
            ):
                body = build_calendar_event_body(
                    date="2026-06-15",
                    time="18:00",
                    name="Иван",
                    phone="+79160001122",
                    service_type="boat",
                    booking_id="bk_test",
                    client_id="client_1",
                    set_count=3,
                )
                assert body["extendedProperties"]["private"]["set_count"] == "3"

    def test_flags_off_boat_duration_30(self, app):
        with app.app_context():
            with patch(
                "app.services.booking.calendar_writer.is_phase2_availability_enabled",
                return_value=False,
            ):
                assert booking_duration_minutes("boat", 3) == 30
