import pytest
from unittest.mock import patch
from flask import Flask
from app.services.responses_api import responses_bp

@pytest.fixture
def client():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(responses_bp)
    return app.test_client()

@patch('app.services.responses_api.get_response')
@patch('app.services.responses_api.save_chat_message')
def test_assistant_success(mock_save, mock_get, client):
    mock_get.return_value = "OK"
    resp = client.post('/api/assistant/', json={'prompt': 'Hello'})
    assert resp.status_code == 200
    assert resp.json == {'response': 'OK'}
    mock_get.assert_called_once()
    mock_save.assert_called_once()

def test_assistant_missing_prompt(client):
    resp = client.post('/api/assistant/', json={})
    assert resp.status_code == 400
    assert 'error' in resp.json

@patch('app.services.responses_api.get_response', side_effect=ValueError("Bad"))
def test_assistant_bad_params(mock_get, client):
    resp = client.post('/api/assistant/', json={'prompt': ''})
    assert resp.status_code == 400 or resp.status_code == 422
    assert 'error' in resp.json

@patch('app.services.responses_api.get_response', side_effect=Exception("Oops"))
def test_assistant_internal_error(mock_get, client):
    resp = client.post('/api/assistant/', json={'prompt': 'Hi'})
    assert resp.status_code == 500
    assert resp.json['error'] == 'Внутренняя ошибка сервера' 