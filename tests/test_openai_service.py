import pytest
from unittest.mock import patch, MagicMock
from app.services.openai_service import get_response, DEFAULT_MODEL, FALLBACK_MODEL

@patch("app.services.openai_service.client")
def test_success(mock_client):
    # Мок-ответ
    mock_resp = MagicMock(choices=[MagicMock(message=MagicMock(content="OK"))])
    mock_client.chat.completions.create.return_value = mock_resp
    assert get_response("Hello") == "OK"
    mock_client.chat.completions.create.assert_called_once_with(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
        ],
    )

@patch("app.services.openai_service.client")
def test_empty_message_raises(mock_client):
    with pytest.raises(ValueError):
        get_response("   ")

@patch("app.services.openai_service.client")
def test_fallback_on_error(mock_client):
    # Fine-tuned падает → fallback срабатывает
    def side_effect(**kwargs):
        raise RuntimeError("Fail FT")
    mock_client.chat.completions.create.side_effect = side_effect
    # Проверяем, что вторая попытка модель=FALLBACK_MODEL
    with patch("app.services.openai_service.get_response", wraps=get_response) as wrapped:
        res = get_response("Hi", model=FALLBACK_MODEL)
        # В релизном UI не показываем сырой текст исключения, а возвращаем короткое сообщение
        assert "не удалось получить ответ" in res.lower()


@patch("app.services.openai_service.client")
@patch("app.services.openai_service.os.getenv")
def test_responses_backend_success(mock_getenv, mock_client):
    mock_getenv.side_effect = lambda key, default=None: {
        "CHAT_BACKEND": "responses",
    }.get(key, default)
    mock_client.responses.create.return_value = MagicMock(output_text="Ответ через Responses API")

    assert get_response("Hello responses") == "Ответ через Responses API"
    mock_client.responses.create.assert_called_once()
    kwargs = mock_client.responses.create.call_args.kwargs
    assert kwargs["model"] == DEFAULT_MODEL
    assert kwargs["instructions"] == "You are a helpful assistant."
    assert kwargs["input"][-1]["role"] == "user"
    assert kwargs["input"][-1]["content"][0]["text"] == "Hello responses"


@patch("app.services.openai_service.client")
@patch("app.services.openai_service.os.getenv")
def test_responses_backend_fallback_on_model_not_found(mock_getenv, mock_client):
    mock_getenv.side_effect = lambda key, default=None: {
        "CHAT_BACKEND": "responses",
    }.get(key, default)

    def _side_effect(**kwargs):
        if kwargs["model"] == "missing-model":
            raise RuntimeError("model_not_found")
        return MagicMock(output_text="Fallback OK")

    mock_client.responses.create.side_effect = _side_effect

    res = get_response("Hello fallback", model="missing-model")
    assert res == "Fallback OK"
    assert mock_client.responses.create.call_count == 2


@patch("app.services.openai_service.client")
@patch("app.services.openai_service.os.getenv")
def test_responses_backend_fallback_on_bad_request(mock_getenv, mock_client):
    """При 400 от Responses API — откат на Chat Completions (тот же промпт/история)."""
    mock_getenv.side_effect = lambda key, default=None: {
        "CHAT_BACKEND": "responses",
    }.get(key, default)
    _BadRequest = type("BadRequestError", (Exception,), {"status_code": 400})
    mock_client.responses.create.side_effect = _BadRequest("param rejected")
    mock_resp = MagicMock(choices=[MagicMock(message=MagicMock(content="Через completions"))])
    mock_client.chat.completions.create.return_value = mock_resp

    assert get_response("Привет") == "Через completions"
    mock_client.responses.create.assert_called_once()
    mock_client.chat.completions.create.assert_called_once()