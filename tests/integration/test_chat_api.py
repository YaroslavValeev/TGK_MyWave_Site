"""
Integration tests for chat API contract.

Ensures:
- /chat/api is the canonical endpoint and responds correctly
- /api/chat (legacy compatibility layer) proxies to the same handler
- Both return expected JSON format without hitting real OpenAI
"""

import json
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def app():
    """Create application for testing."""
    from app import create_app
    return create_app(config_name='testing')


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def _mock_ask(message, **kwargs):
    """Mock OpenAI ask - returns fixed response."""
    return "Тестовый ответ от AI"


def _mock_get_response_with_knowledge(prompt):
    """Mock knowledge-base response."""
    return "Тестовый ответ из базы знаний"


@pytest.mark.parametrize('endpoint', ['/chat/api', '/api/chat'])
def test_chat_endpoints_available_and_respond(client, endpoint):
    """Both /chat/api and /api/chat are available and return valid JSON."""
    with patch('app.routes.chat.ask', side_effect=_mock_ask), \
         patch('app.services.responses_api.get_response_with_knowledge', side_effect=_mock_get_response_with_knowledge):
        response = client.post(
            endpoint,
            data=json.dumps({'message': 'Привет'}),
            content_type='application/json',
        )
    assert response.status_code == 200, f"Expected 200 for {endpoint}, got {response.status_code}"
    data = response.get_json()
    assert data is not None, f"Response should be JSON for {endpoint}"
    assert 'response' in data or 'error' in data or 'reply' in data, \
        f"Response should have 'response', 'error' or 'reply' for {endpoint}: {data}"


def test_chat_api_canonical_returns_expected_format(client):
    """POST /chat/api returns expected JSON format (response key)."""
    with patch('app.routes.chat.ask', side_effect=_mock_ask), \
         patch('app.services.responses_api.get_response_with_knowledge', return_value=None):
        response = client.post(
            '/chat/api',
            data=json.dumps({'message': 'Тест'}),
            content_type='application/json',
        )
    assert response.status_code == 200
    data = response.get_json()
    assert 'response' in data, f"Expected 'response' in JSON: {data}"
    assert isinstance(data['response'], str) or data['response'] is None


def test_api_chat_proxies_to_chat_handler(client):
    """POST /api/chat proxies to real chat handler (same behavior as /chat/api)."""
    with patch('app.routes.chat.ask', side_effect=_mock_ask), \
         patch('app.services.responses_api.get_response_with_knowledge', return_value=None):
        resp_canonical = client.post(
            '/chat/api',
            data=json.dumps({'message': 'Proxy test'}),
            content_type='application/json',
        )
        resp_legacy = client.post(
            '/api/chat',
            data=json.dumps({'message': 'Proxy test'}),
            content_type='application/json',
        )
    assert resp_canonical.status_code == 200
    assert resp_legacy.status_code == 200
    data_c = resp_canonical.get_json()
    data_l = resp_legacy.get_json()
    assert 'response' in data_c
    assert 'response' in data_l or 'reply' in data_l


def test_chat_api_rejects_empty_message(client):
    """POST /chat/api returns 400 for empty or missing message."""
    response = client.post(
        '/chat/api',
        data=json.dumps({}),
        content_type='application/json',
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data is not None and ('error' in data or 'message' in str(data).lower())
