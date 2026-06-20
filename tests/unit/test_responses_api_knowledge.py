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


def test_try_offline_kb_reply_formats_snippets():
    from app.services.responses_api import try_offline_kb_reply

    out = try_offline_kb_reply(["Первый абзац про кемп.", "Второй абзац с деталями."])
    assert out
    assert "кемп" in out.lower()
    assert "запис" in out.lower() or "слот" in out.lower()


def test_is_openai_failure_reply():
    from app.services.responses_api import is_openai_failure_reply

    assert is_openai_failure_reply("Сейчас не удалось получить ответ.")
    assert is_openai_failure_reply(
        "Сейчас умный ассистент временно недоступен с нашего сервера."
    )
    assert not is_openai_failure_reply("Тренировка в зале длится 60 минут.")


def test_get_response_with_knowledge_returns_none_without_kb_hits(app):
    with app.app_context():
        app.config["OPENAI_API_KEY"] = "test-key-for-unit"
        with patch("app.services.responses_api.get_knowledge", return_value=jsonify([])):
            from app.services.responses_api import get_response_with_knowledge

            out = get_response_with_knowledge("привет без ключевых слов знаний")
    assert out is None


def test_collect_snippets_safari_not_challenge(app):
    with app.app_context():
        from app.services.responses_api import _collect_knowledge_snippets

        for question in (
            "как попасть в проект wakesurf safari",
            "я хочу на сафари",
        ):
            snippets = _collect_knowledge_snippets(question)
            assert snippets, f"ожидали KB для: {question}"
            joined = " ".join(snippets).lower()
            assert "safari" in joined or "сафари" in joined
            assert "wake challenge" not in joined
            assert "соревновательный проект" not in joined


def test_collect_snippets_challenge_when_asked(app):
    with app.app_context():
        from app.services.responses_api import _collect_knowledge_snippets

        snippets = _collect_knowledge_snippets("как участвовать в wakesurf challenge")
        joined = " ".join(snippets).lower()
        assert "challenge" in joined or "челлендж" in joined
        assert "wake challenge" in joined or "соревновательный" in joined
        assert "wake surf safari" not in joined or "флагманский" not in joined


def test_try_direct_what_to_bring_reply_boat():
    from app.services.responses_api import try_direct_what_to_bring_reply

    out = try_direct_what_to_bring_reply("что взять на катер?")
    assert out
    assert "купальник" in out.lower() or "полотенц" in out.lower()
    assert "зал или на катер" not in out.lower()


def test_try_direct_what_to_bring_reply_ambiguous_none():
    from app.services.responses_api import try_direct_what_to_bring_reply

    assert try_direct_what_to_bring_reply("что нужно с собой взять?") is None
