import pytest
from app import create_app
from app.services.safari_cms_service import SafariCMSService


@pytest.fixture(scope='module')
def test_app():
    app = create_app('testing')
    app.config['SAFARI_SYNC_KEY'] = 'testkey'
    with app.test_client() as client:
        with app.app_context():
            yield client


def test_sync_endpoint_requires_key(monkeypatch, test_app):
    client = test_app

    # monkeypatch the sync_all to avoid real Google calls
    monkeypatch.setattr(SafariCMSService, 'sync_all', staticmethod(lambda: {'success': True, 'total_synced': 0}))

    # no key -> unauthorized
    rv = client.post('/api/safari/sync')
    assert rv.status_code == 401

    # wrong key -> unauthorized
    rv = client.post('/api/safari/sync', headers={'X-SAFARI-SYNC-KEY': 'wrong'})
    assert rv.status_code == 401

    # correct key -> ok
    rv = client.post('/api/safari/sync', headers={'X-SAFARI-SYNC-KEY': 'testkey'})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['ok'] is True
    assert data['result']['success'] is True
