import pytest
from app import create_app
from app.database.models import db


@pytest.fixture
def app():
    app = create_app('testing')
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
    })
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_booking_api_with_mocks(monkeypatch, client):
    # Mock external integrations: booking_utils, crm, sheets, calendar
    monkeypatch.setattr('app.modules.booking_utils.is_slot_available', lambda d, t: (True, ''))
    monkeypatch.setattr('app.services.crm.create_lead', lambda data: {'id': 'mock'})
    monkeypatch.setattr('app.services.sheets_writer.save_client_workout_to_sheets', lambda **k: None)
    monkeypatch.setattr('app.services.sheets_writer.save_sales_deal_to_sheets', lambda **k: None)
    monkeypatch.setattr('app.modules.calendar_integration.create_calendar_event', lambda d: None)

    resp = client.post('/booking/api/book', json={
        'name': 'Иван',
        'phone': '+70000000000',
        'date': '2025-10-20',
        'time': '10:00'
    })
    assert resp.status_code == 200
    assert resp.json.get('success') is True
    assert 'Booking' in resp.json.get('message') or 'created' in resp.json.get('message')
