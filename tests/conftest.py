import pytest
from app import create_app
import unittest.mock as umock


@pytest.fixture(scope='session')
def app():
    app = create_app('testing')
    yield app


@pytest.fixture(scope='function')
def client(app):
    return app.test_client()


@pytest.fixture
def mocker():
    """Simple replacement for pytest-mock's `mocker` when it's not installed.

    Provides a `.patch(target, **kwargs)` method that starts a patch and
    ensures it's stopped after the test ends.
    """
    started = []

    class _Mocker:
        def patch(self, target, **kwargs):
            p = umock.patch(target, **kwargs)
            started.append(p)
            return p.start()

    m = _Mocker()
    yield m
    # stop in reverse order
    for p in reversed(started):
        try:
            p.stop()
        except Exception:
            pass


@pytest.fixture(autouse=True)
def mock_external_apis(mocker):
    # patch common external integrations
    mocker.patch('app.services.google_sheets_service.append_record', return_value=True)
    mocker.patch('app.services.openai_service.ask', return_value='Тестовый ответ')