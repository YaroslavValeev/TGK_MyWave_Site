"""Проверка info-intent: get_response_with_knowledge использует общий Responses transport."""

from unittest.mock import patch

from flask import jsonify


def test_get_response_with_knowledge_uses_responses_transport(app):
    with app.app_context():
        app.config["OPENAI_API_KEY"] = "test-key-for-unit"
        with patch(
            "app.services.responses_api.get_knowledge",
            return_value=jsonify(["фрагмент один", "фрагмент два"]),
        ), patch(
            "app.services.responses_api.responses_text_reply",
            return_value="Ответ по базе знаний.",
        ) as mocked_reply:
            from app.services.responses_api import get_response_with_knowledge

            out = get_response_with_knowledge(
                "подскажи про тренировку в зале",
                mw_chat_context={
                    "entry": "services",
                    "kind": "service",
                    "id": "gym",
                    "title": "Зал",
                },
            )

    assert out and "Ответ по базе" in out
    mocked_reply.assert_called_once()
    kwargs = mocked_reply.call_args.kwargs
    assert kwargs["source"] == "knowledge"
    assert kwargs["temperature"] == 0.7
    assert "фрагмент один" in kwargs["instructions"]
    assert "ЗАЛА" in kwargs["instructions"] or "помещении" in kwargs["instructions"]
    assert kwargs["history"] == []


def test_get_response_with_knowledge_returns_none_without_kb_hits(app):
    with app.app_context():
        app.config["OPENAI_API_KEY"] = "test-key-for-unit"
        with patch("app.services.responses_api.get_knowledge", return_value=jsonify([])):
            from app.services.responses_api import get_response_with_knowledge

            out = get_response_with_knowledge("привет без ключевых слов знаний")
    assert out is None
