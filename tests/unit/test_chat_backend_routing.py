"""Маршрутизация CHAT_BACKEND: auto → completions для сайта по умолчанию."""


def test_auto_without_use_assistant_prefers_completions():
    from app.services.openai_service import _chat_backend

    cfg = {"CHAT_BACKEND": "auto", "ASSISTANT_ID": "asst_test123"}
    assert _chat_backend(cfg) == "completions"


def test_auto_with_use_assistant_keeps_legacy_auto():
    from app.services.openai_service import _chat_backend

    cfg = {
        "CHAT_BACKEND": "auto",
        "ASSISTANT_ID": "asst_test123",
        "CHAT_USE_ASSISTANT": True,
    }
    assert _chat_backend(cfg) == "auto"


def test_default_backend_is_completions(monkeypatch):
    monkeypatch.delenv("CHAT_BACKEND", raising=False)
    monkeypatch.delenv("CHAT_USE_ASSISTANT", raising=False)
    from app.services.openai_service import _chat_backend

    assert _chat_backend({}) == "completions"
