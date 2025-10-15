import os
os.environ['MYWAVE_DISABLE_FILE_LOG'] = '1'

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


def test_booking_api_calls_crm_and_sheets(monkeypatch, client):
    import os
    os.environ['MYWAVE_DISABLE_FILE_LOG'] = '1'
    called = {"crm": False, "sheet": False}

    def fake_create_lead(data):
        called['crm'] = True
        return {"id": "fake_lead"}

    def fake_save_sales_deal_to_sheets(**kwargs):
        called['sheet'] = True

    monkeypatch.setattr('app.services.crm.create_lead', fake_create_lead)
    # patch the services used by booking_orchestrator so orchestration triggers our fakes
    monkeypatch.setattr('app.services.sheets_writer.save_sales_deal_to_sheets', fake_save_sales_deal_to_sheets)
    # Prevent any Google Sheets / Calendar calls triggered from modules used by orchestrator
    monkeypatch.setattr('app.modules.sheets.append_row', lambda *a, **k: None)
    monkeypatch.setattr('app.modules.calendar_integration.create_calendar_event', lambda *a, **k: None)

    resp = client.post('/booking/api/book', json={
        "name": "Ivan",
        "phone": "+70000000000",
        "date": "2025-10-20",
        "time": "10:00"
    })
    assert resp.status_code == 200
    assert resp.json.get('success') is True
    assert called['crm'] is True
    assert called['sheet'] is True
