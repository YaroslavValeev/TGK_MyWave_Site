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
        messages=[{"role": "user", "content": "Hello"}],
        temperature=0.7,
        max_tokens=1000,
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
    with patch(
        "app.services.openai_service.get_response", wraps=get_response
    ) as wrapped:
        res = get_response("Hi", model=FALLBACK_MODEL)
        assert "Fail FT" in res
