import pytest

from flask import Flask

from app.services import crm


@pytest.fixture
def app():
    app = Flask(__name__)
    # minimal config required by sheets_writer
    app.config["SPREADSHEET_ID"] = "test-spreadsheet"
    app.config["CRM_PROVIDER"] = None
    app.config["TESTING"] = True
    return app


def test_create_lead_falls_back_to_sheets(monkeypatch, app):
    called = {}

    def fake_save_client_to_sheets(**kwargs):
        called['args'] = kwargs

    monkeypatch.setattr(crm.sheets_writer, 'save_client_to_sheets', fake_save_client_to_sheets)

    with app.app_context():
        resp = crm.create_lead({"name": "Ivan", "phone": "+70000000000", "source": "web"})

    assert resp["status"] == "saved_to_sheets"
    assert called.get('args') is not None
    assert called['args']["name"] == "Ivan"
    assert called['args']["phone"] == "+70000000000"
