import os
import sys
import pytest

# Ensure repo root is on sys.path so tests can import the `app` package when
# pytest is executed from different working directories or under CI.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app

@pytest.fixture(scope='session')
def app():
    app = create_app('testing')
    yield app

@pytest.fixture(scope='function')
def client(app):
    return app.test_client()

@pytest.fixture(autouse=True)
def mock_external_apis(mocker):
    mocker.patch('app.services.google_sheets_service.append_record', return_value=True)
    mocker.patch('app.services.openai_service.ask', return_value='Тестовый ответ') 