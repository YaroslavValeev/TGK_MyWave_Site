import pytest
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