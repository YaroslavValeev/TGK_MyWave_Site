"""
Integration tests for chat API contract.

Ensures:
- /chat/api is the canonical endpoint and responds correctly
- /api/chat (legacy compatibility layer) proxies to the same handler
- Both return expected JSON format without hitting real OpenAI
- GET /chat/ отдаёт страницу с виджетом
- Сценарий брони обрабатывается через тот же POST /chat/api (server-first)
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


def test_chat_page_get_returns_200(client):
    """Страница чата доступна и содержит плавающий виджет."""
    response = client.get('/chat/')
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert 'chat-widget' in text or 'floating-chat' in text
    assert 'csrf_token' in text or 'csrf-token' in text


def test_chat_page_without_trailing_slash_returns_200(client):
    """GET /chat (без слэша) не даёт 404 — strict_slashes=False у blueprint чата."""
    response = client.get('/chat')
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert 'chat-widget' in text or 'floating-chat' in text


def test_booking_intent_handled_via_chat_api(client):
    """Ключевое слово записи обрабатывается внутри /chat/api (без отдельного вызова /api/booking с клиента)."""
    with patch('app.services.booking_orchestrator.orchestrate') as orch:
        orch.return_value = ('Выберите дату', {'step': 'ask_date'})
        response = client.post(
            '/chat/api',
            data=json.dumps({'message': 'хочу записаться завтра'}),
            content_type='application/json',
        )
    assert response.status_code == 200
    data = response.get_json()
    assert data.get('response')
    assert data.get('state', {}).get('step') == 'ask_date'
    orch.assert_called_once()


def test_chat_context_from_body_stored_in_session(client):
    """Поле context в теле запроса сохраняется в сессии для связи чата с разделом сайта."""
    with patch('app.routes.chat.ask', side_effect=_mock_ask), \
         patch('app.services.responses_api.get_response_with_knowledge', return_value=None):
        client.post(
            '/chat/api',
            data=json.dumps({
                'message': 'Привет',
                'context': {'entry': 'shop', 'kind': 'section', 'title': 'Магазин', 'id': ''},
            }),
            content_type='application/json',
        )
    with client.session_transaction() as sess:
        ctx = sess.get('mw_chat_context') or {}
        assert ctx.get('entry') == 'shop'
        assert 'Магазин' in (ctx.get('title') or '')


def test_mw_context_merged_into_booking_state_for_orchestrator(client):
    """При сценарии брони в orchestrate передаётся mw_context из сессии."""
    with client.session_transaction() as sess:
        sess['mw_chat_context'] = {
            'entry': 'services',
            'kind': 'service',
            'id': 'gym',
            'title': 'Зал',
        }
    with patch('app.services.booking_orchestrator.orchestrate') as orch:
        orch.return_value = ('Выберите дату', {'step': 'ask_date'})
        client.post(
            '/chat/api',
            data=json.dumps({'message': 'хочу записаться'}),
            content_type='application/json',
        )
    orch.assert_called_once()
    _msg, state_in = orch.call_args[0]
    assert state_in.get('mw_context', {}).get('id') == 'gym'


def test_booking_branch_persists_chat_turn(client):
    """После ответа сценария брони вызывается сохранение пары реплик в БД."""
    with patch('app.services.booking_orchestrator.orchestrate') as orch, \
         patch('app.routes.chat._save_chat_turn') as save_turn:
        orch.return_value = ('Выберите дату', {'step': 'ask_date'})
        client.post(
            '/chat/api',
            data=json.dumps({'message': 'запишите меня завтра'}),
            content_type='application/json',
        )
    save_turn.assert_called_once()


def test_chat_api_responses_backend_keeps_contract(client, app):
    """При CHAT_BACKEND=responses контракт /chat/api не меняется."""
    import app.services.openai_service as oa

    old_client = oa.client
    try:
        oa.client = MagicMock()
        oa.client.responses.create.return_value = MagicMock(output_text="Ответ через Responses API")
        app.config["CHAT_BACKEND"] = "responses"
        app.config["OPENAI_API_KEY"] = "test-openai-key"
        response = client.post(
            '/chat/api',
            data=json.dumps({'message': 'Привет через responses'}),
            content_type='application/json',
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert "Responses API" in data["response"]
        oa.client.responses.create.assert_called_once()
    finally:
        oa.client = old_client


def test_chat_api_asks_disambiguation_for_general_what_to_bring(client):
    """Если контекст не задан и вопрос про «что взять», чат сначала уточняет: зал или катер."""
    response = client.post(
        '/chat/api',
        data=json.dumps({'message': 'Что нужно с собой взять?'}),
        content_type='application/json',
    )
    assert response.status_code == 200
    data = response.get_json() or {}
    text = (data.get('response') or '').lower()
    assert 'зал' in text and 'катер' in text


def test_chat_api_boat_what_to_bring_direct_checklist(client):
    """«Что взять на катер?» — прямой чек-лист без уточнения зал/катер."""
    response = client.post(
        '/chat/api',
        data=json.dumps({'message': 'Что взять на катер?'}),
        content_type='application/json',
    )
    assert response.status_code == 200
    data = response.get_json() or {}
    text = (data.get('response') or '').lower()
    assert 'катер' in text or 'купальник' in text or 'полотенц' in text
    assert 'вам нужна запись в зал или на катер' not in text


def test_chat_info_uses_offline_kb_when_openai_fails(client):
    """При сбое OpenAI info-вопрос отвечает из KB (geo-block / 403)."""
    with patch(
        'app.routes.chat.ask',
        return_value='Сейчас не удалось получить ответ. Попробуйте ещё раз чуть позже.',
    ):
        response = client.post(
            '/chat/api',
            data=json.dumps({'message': 'как попасть в кемп?'}),
            content_type='application/json',
        )
    assert response.status_code == 200
    data = response.get_json() or {}
    text = (data.get('response') or '').lower()
    assert 'кемп' in text or 'ruza' in text or 'заявк' in text
    assert 'не удалось получить ответ' not in text


def test_chat_info_uses_openai_when_available(client):
    """При успешном OpenAI — ответ модели, не сырой текст KB."""
    with patch('app.routes.chat.ask', return_value='Запишитесь через форму на сайте, помогу с датами.'):
        response = client.post(
            '/chat/api',
            data=json.dumps({'message': 'как попасть в кемп?'}),
            content_type='application/json',
        )
    assert response.status_code == 200
    data = response.get_json() or {}
    assert 'форму' in (data.get('response') or '').lower()
