import pytest
from datetime import date

from app import create_app
from app.database.models import db, Document
from app.services.safari_cms_service import SafariCMSService


@pytest.fixture(scope='module')
def test_app():
    app = create_app('testing')
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


class DummyWorksheet:
    def __init__(self, rows):
        self._rows = rows

    def get_all_records(self):
        return self._rows


class DummyGSheet:
    def __init__(self, sheets):
        # sheets: dict name->rows
        self.sheets = sheets

    def open(self, name):
        # return self-like with worksheet method
        that = self

        class W:
            def __init__(self, sheets):
                self.sheets = sheets

            def worksheet(self, sheet_name):
                rows = that.sheets.get(sheet_name, [])
                return DummyWorksheet(rows)

        return W(self.sheets)


def test_sync_routes_and_faq(monkeypatch, test_app):
    # Prepare fake sheet data
    routes_rows = [
        {
            'route_id': 'r1',
            'name': 'Route One',
            'description': 'Nice route',
            'price': '1000',
            'duration_days': '2',
            'difficulty_level': 'beginner',
            'capacity': '6',
            'highlights': 'Sunset,Camp'
        }
    ]
    faq_rows = [
        {
            'question': 'What to bring?',
            'answer': 'Swimwear',
            'category': 'preparation',
            'order': '1'
        }
    ]

    dummy = DummyGSheet({'Safari_Routes': routes_rows, 'Safari_FAQ': faq_rows})

    # monkeypatch get_gsheet to return dummy (module uses lazy import)
    # The service imports get_gsheet from app.services.google at call time, so insert a fake module into sys.modules
    import types, sys
    fake_google_mod = types.SimpleNamespace(get_gsheet=lambda: dummy)
    monkeypatch.setitem(sys.modules, 'app.services.google', fake_google_mod)

    # call sync methods
    routes_res = SafariCMSService.sync_routes()
    faq_res = SafariCMSService.sync_faq()

    assert routes_res['success'] is True
    assert routes_res['count'] == 1

    assert faq_res['success'] is True
    assert faq_res['count'] == 1

    # verify DB entries
    routes = SafariCMSService.get_routes()
    assert len(routes) == 1
    assert routes[0]['route_id'] == 'r1'

    faqs = SafariCMSService.get_faq()
    assert len(faqs) == 1
    assert faqs[0]['question'] == 'What to bring?'
