"""Boat public booking via YCLIENTS SoT (in-process provider)."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.booking.pipeline import (
    CalendarBookingError,
    execute_web_booking,
)
from app.services.booking.providers.base import ProviderBookingResult, ProviderSlot


class TestBoatYclientsSlots:
    def test_get_boat_slots_uses_yclients(self, app, monkeypatch):
        monkeypatch.setenv("BOAT_PROVIDER", "yclients")
        monkeypatch.setenv("YCLIENTS_ENABLED", "1")
        monkeypatch.setenv("YCLIENTS_READ_ONLY_ENABLED", "1")
        monkeypatch.setenv("YCLIENTS_WRITE_ENABLED", "0")

        provider = MagicMock()
        provider.fetch_available_slots.return_value = [
            ProviderSlot(start_time="19:00", duration_minutes=25, available=True),
            ProviderSlot(start_time="19:30", duration_minutes=25, available=False),
            ProviderSlot(start_time="20:00", duration_minutes=25, available=True),
        ]

        with app.app_context():
            with patch(
                "app.services.booking.providers.yclients.get_yclients_provider",
                return_value=provider,
            ):
                from app.routes.calendar_routes import get_boat_slots

                slots = get_boat_slots("2026-07-31")

        assert slots == [
            {"time": "19:00", "available": True},
            {"time": "20:00", "available": True},
        ]
        provider.fetch_available_slots.assert_called_once_with("2026-07-31")


class TestBoatYclientsCreate:
    def test_create_uses_yclients_skips_calendar(self, app, monkeypatch):
        monkeypatch.setenv("BOAT_PROVIDER", "yclients")
        monkeypatch.setenv("YCLIENTS_ENABLED", "1")
        monkeypatch.setenv("YCLIENTS_READ_ONLY_ENABLED", "1")
        monkeypatch.setenv("YCLIENTS_WRITE_ENABLED", "1")

        provider = MagicMock()
        provider.create_booking.return_value = ProviderBookingResult(
            external_id="1870491744",
            status="waiting",
            raw={},
        )

        with app.app_context():
            with (
                patch(
                    "app.services.booking.pipeline.is_duplicate_web_booking",
                    return_value=False,
                ),
                patch(
                    "app.services.booking.pipeline.generate_booking_id",
                    return_value="bk_site_1",
                ),
                patch(
                    "app.services.booking.pipeline.resolve_client",
                    return_value=MagicMock(client_id="c_site"),
                ),
                patch(
                    "app.services.booking.providers.yclients.get_yclients_provider",
                    return_value=provider,
                ),
                patch(
                    "app.services.booking.pipeline.create_calendar_event"
                ) as mock_cal,
                patch("app.services.booking.pipeline.write_workout_row") as mock_w,
                patch(
                    "app.services.booking.pipeline.write_client_workout_row",
                    return_value="cw_yc",
                ) as mock_cw,
            ):
                result = execute_web_booking(
                    date="2026-07-31",
                    time="19:00",
                    name="Ярослав",
                    phone="+79161234567",
                    service_type="boat",
                    set_count=1,
                )

        assert result.workout_id == "yc-1870491744"
        assert result.client_workout_id == "cw_yc"
        mock_cal.assert_not_called()
        mock_w.assert_called_once()
        assert mock_w.call_args.kwargs["workout_id"] == "yc-1870491744"
        mock_cw.assert_called_once()
        provider.create_booking.assert_called_once()
        assert provider.create_booking.call_args.kwargs["source"] == "site"
        assert provider.create_booking.call_args.kwargs["use_online"] is False

    def test_yclients_create_failure_raises(self, app, monkeypatch):
        monkeypatch.setenv("BOAT_PROVIDER", "yclients")
        monkeypatch.setenv("YCLIENTS_ENABLED", "1")
        monkeypatch.setenv("YCLIENTS_READ_ONLY_ENABLED", "1")
        monkeypatch.setenv("YCLIENTS_WRITE_ENABLED", "1")

        provider = MagicMock()
        provider.create_booking.side_effect = RuntimeError("yc down")

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
                    "app.services.booking.providers.yclients.get_yclients_provider",
                    return_value=provider,
                ),
                patch("app.services.booking.pipeline.write_workout_row") as mock_w,
            ):
                with pytest.raises(CalendarBookingError):
                    execute_web_booking(
                        date="2026-07-31",
                        time="19:00",
                        name="Test",
                        phone="+79160000000",
                        service_type="boat",
                    )
                mock_w.assert_not_called()
