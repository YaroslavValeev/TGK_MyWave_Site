import json
from datetime import datetime, timedelta

import pytest

from app import create_app, db


@pytest.fixture
def app():
    app = create_app(config_name="testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_services_pages(client):
    # services blueprint page
    resp = client.get("/services/wakesurf-safari")
    assert resp.status_code == 200

    # safari blueprint page
    resp2 = client.get("/wakesurf-safari/")
    assert resp2.status_code == 200


def test_contact_form_post_with_fallback(monkeypatch, client, app):
    """Simulate WTForms validation error to trigger fallback validator path."""
    from app.forms.contact_form import ContactForm

    # make validate_on_submit raise an exception to trigger fallback
    def _raise(self):
        raise Exception("Simulated validation failure")

    monkeypatch.setattr(ContactForm, "validate_on_submit", _raise)

    payload = {
        "name": "Test User",
        "email": "test@example.com",
        "message": "Hello from test",
    }

    resp = client.post("/contact", data=payload, follow_redirects=True)
    # on success code redirects back to /contact and returns 200
    assert resp.status_code in (200, 302)

    # Ensure Contact was saved to DB
    from app.database.models import Contact

    with app.app_context():
        cnt = Contact.query.filter_by(email="test@example.com").count()
        assert cnt >= 1


def test_get_slots_and_booking(monkeypatch, client):
    """Test slots endpoint and booking endpoint with monkeypatched dependencies."""
    import app.routes.calendar_routes as cal

    # Provide a predictable slot
    slot = {"time": "10:00", "available": True, "remaining": 3}
    monkeypatch.setattr(cal, "get_available_slots", lambda date: [slot])

    future = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    resp = client.get(f"/api/calendar/slots/{future}")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert isinstance(data, list)

    # Monkeypatch CSRF check in the csrf service used by the endpoint
    monkeypatch.setattr("app.services.csrf.check_csrf", lambda: True, raising=True)
    monkeypatch.setattr(cal, "find_or_create_client", lambda phone, name: "client_test")
    monkeypatch.setattr(cal, "find_workout", lambda date, time: ("workout_1", 0, 0))
    monkeypatch.setattr(cal, "append_record", lambda *a, **k: None)
    monkeypatch.setattr(cal, "update_workout_capacity", lambda *a, **k: None)
    monkeypatch.setattr(cal, "add_event_to_calendar", lambda *a, **k: None)

    booking_payload = {
        "date": future,
        "time": "10:00",
        "name": "Tester",
        "phone": "+71234567890",
    }

    resp2 = client.post("/api/calendar/book", json=booking_payload)
    assert resp2.status_code in (200, 201)
    js = json.loads(resp2.data)
    assert "message" in js or "success" in js
