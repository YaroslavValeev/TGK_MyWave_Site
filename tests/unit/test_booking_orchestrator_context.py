"""Контекст страницы (mw_context) в сценарии бронирования через чат."""
from unittest.mock import patch

import pytest


@pytest.fixture
def base_state():
    return {
        "step": "ask_date",
        "mw_context": {"entry": "services", "title": "Зал", "kind": "service", "id": "gym"},
    }


def test_ask_date_reply_includes_context_title(base_state):
    from app.services import booking_orchestrator as bo

    empty_model = {
        "error": True,
        "entities": {},
        "next_step": "ask_date",
        "tool_calls": [],
    }
    with patch.object(bo, "respond_structured", return_value=empty_model):
        text, st = bo.orchestrate("здравствуйте", base_state)
    assert "Зал" in text or "«Зал»" in text
    assert "дату" in text.lower()


def test_ask_date_reply_mentions_shop_without_title():
    from app.services import booking_orchestrator as bo

    state = {"step": "ask_date", "mw_context": {"entry": "shop", "title": "", "kind": "section", "id": ""}}
    empty_model = {"error": True, "entities": {}, "next_step": "ask_date", "tool_calls": []}
    with patch.object(bo, "respond_structured", return_value=empty_model):
        text, _st = bo.orchestrate("привет", state)
    assert "магазин" in text.lower()
