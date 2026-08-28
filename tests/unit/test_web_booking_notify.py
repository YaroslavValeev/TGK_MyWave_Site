"""Web booking notifies admin via Telegram (best-effort, never breaks 201)."""

from unittest.mock import patch

from app.services.booking.pipeline import BookingResult


def test_notify_helper_swallows_telegram_errors(app):
    from app.routes.calendar_routes import _notify_web_booking_best_effort

    with app.app_context():
        with patch(
            "app.services.application_notifications.notify_web_booking",
            side_effect=RuntimeError("tg down"),
        ):
            _notify_web_booking_best_effort(
                name="Анна",
                phone="+79160001122",
                service_type="boat",
                date="2026-08-30",
                time="10:00",
                booking_id="bk_1",
                workout_id="w1",
            )


def test_calendar_book_calls_notify_and_returns_201(app):
    result = BookingResult(
        workout_id="w1",
        client_id="c1",
        booking_id="bk_1",
        client_workout_id="cw1",
    )
    app.config["SPREADSHEET_ID"] = "test-sheet-id"
    payload = {
        "date": "2026-08-30",
        "time": "10:00",
        "name": "Анна",
        "phone": "+79160001122",
        "service_type": "boat",
    }
    with patch("app.services.csrf.check_csrf", return_value=True), patch(
        "app.routes.calendar_routes.read_records", return_value=[]
    ), patch(
        "app.routes.calendar_routes.get_boat_slots",
        return_value=[{"time": "10:00", "available": True, "remaining": 1}],
    ), patch(
        "app.config.booking_features.is_phase2_availability_enabled",
        return_value=False,
    ), patch(
        "app.services.booking.execute_web_booking", return_value=result
    ), patch(
        "app.routes.calendar_routes.log_analytics_event"
    ), patch(
        "app.routes.calendar_routes._notify_web_booking_best_effort"
    ) as mock_notify:
        client = app.test_client()
        resp = client.post(
            "/api/calendar/book",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 201, resp.get_json()
        body = resp.get_json()
        assert body.get("status") == "success"
        mock_notify.assert_called_once()
        kwargs = mock_notify.call_args.kwargs
        assert kwargs["service_type"] == "boat"
        assert kwargs["name"] == "Анна"
        assert kwargs["booking_id"] == "bk_1"


def test_calendar_book_201_when_notify_raises(app):
    result = BookingResult(
        workout_id="w1",
        client_id="c1",
        booking_id="bk_1",
        client_workout_id="cw1",
    )
    app.config["SPREADSHEET_ID"] = "test-sheet-id"
    payload = {
        "date": "2026-08-30",
        "time": "10:00",
        "name": "Анна",
        "phone": "+79160001122",
        "service_type": "boat",
    }

    with patch("app.services.csrf.check_csrf", return_value=True), patch(
        "app.routes.calendar_routes.read_records", return_value=[]
    ), patch(
        "app.routes.calendar_routes.get_boat_slots",
        return_value=[{"time": "10:00", "available": True, "remaining": 1}],
    ), patch(
        "app.config.booking_features.is_phase2_availability_enabled",
        return_value=False,
    ), patch(
        "app.services.booking.execute_web_booking", return_value=result
    ), patch(
        "app.routes.calendar_routes.log_analytics_event"
    ), patch(
        "app.services.application_notifications.notify_web_booking",
        side_effect=RuntimeError("tg down"),
    ):
        client = app.test_client()
        resp = client.post(
            "/api/calendar/book",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 201, resp.get_json()
        assert resp.get_json().get("status") == "success"
