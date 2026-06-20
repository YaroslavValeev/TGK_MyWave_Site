"""Unit tests for Knowledge Base v2 (parser, loader, matcher, direct replies)."""
from __future__ import annotations

from pathlib import Path

import pytest

SAMPLE_MD = """---
id: test_doc
title: Тестовый документ
category: boat
priority: high
updated_at: 2026-06-19
cta_type: booking_boat
---

# Заголовок

## Когда использовать

- тестовый триггер
- ещё триггер

## Короткий ответ

Короткий тестовый ответ.

## Подробный ответ

Подробный текст для теста.

## Не говорить

- не обещать лишнего

## CTA

Запишитесь на катер.

## Тестовые вопросы

- Тестовый вопрос один?
- Второй тестовый вопрос?
"""


def test_parse_kb_file_sections(tmp_path):
    from app.services.kb_chat.parser import parse_kb_file

    path = tmp_path / "sample.md"
    path.write_text(SAMPLE_MD, encoding="utf-8")
    doc = parse_kb_file(path)
    assert doc is not None
    assert doc.id == "test_doc"
    assert doc.category == "boat"
    assert doc.cta_type == "booking_boat"
    assert doc.short_answer == "Короткий тестовый ответ."
    assert len(doc.triggers) == 2
    assert len(doc.test_questions) == 2


def test_load_index_wave1(app):
    with app.app_context():
        from app.services.kb_chat.loader import clear_cache, load_index

        clear_cache()
        docs = load_index()
        assert len(docs) >= 10
        ids = {d.id for d in docs}
        assert "boat_what_to_bring" in ids
        assert "boat_prices" in ids
        assert "gym_prices" in ids


def test_list_by_category(app):
    with app.app_context():
        from app.services.kb_chat.loader import clear_cache, list_by_category

        clear_cache()
        boat = list_by_category("boat")
        assert len(boat) >= 4


def test_find_best_match_price_boat(app):
    with app.app_context():
        from app.services.kb_chat.loader import clear_cache
        from app.services.kb_chat.matcher import find_best_match

        clear_cache()
        doc = find_best_match("сколько стоит катер?", category="boat")
        assert doc is not None
        assert doc.id == "boat_prices"


def test_try_direct_kb_reply_boat_price(app):
    with app.app_context():
        from app.services.kb_chat.direct_replies import try_direct_kb_reply
        from app.services.kb_chat.loader import clear_cache

        clear_cache()
        reply = try_direct_kb_reply("сколько стоит катер?")
        assert reply is not None
        assert "10 000" in reply.text
        assert "25" in reply.text
        assert reply.cta_type == "booking_boat"


def test_try_direct_kb_reply_gym_price(app):
    with app.app_context():
        from app.services.kb_chat.direct_replies import try_direct_kb_reply
        from app.services.kb_chat.loader import clear_cache

        clear_cache()
        reply = try_direct_kb_reply("сколько стоит тренировка в зале?")
        assert reply is not None
        assert "3 500" in reply.text
        assert reply.cta_type == "booking_gym"


def test_try_direct_kb_reply_booking_disambiguation(app):
    with app.app_context():
        from app.services.kb_chat.direct_replies import try_direct_kb_reply
        from app.services.kb_chat.loader import clear_cache

        clear_cache()
        reply = try_direct_kb_reply("как записаться?")
        assert reply is not None
        assert "катер" in reply.text.lower() and "зал" in reply.text.lower()
        assert reply.cta_type == "booking_choose"
        assert reply.suggestions == ["Катер", "Зал"]


def test_try_direct_what_to_bring_boat(app):
    with app.app_context():
        from app.services.kb_chat.direct_replies import try_direct_what_to_bring_reply
        from app.services.kb_chat.loader import clear_cache

        clear_cache()
        reply = try_direct_what_to_bring_reply("что взять на катер?")
        assert reply is not None
        assert "купальник" in reply.text.lower() or "полотенц" in reply.text.lower()


def test_try_direct_what_to_bring_ambiguous_none(app):
    with app.app_context():
        from app.services.kb_chat.direct_replies import try_direct_what_to_bring_reply

        assert try_direct_what_to_bring_reply("что нужно с собой взять?") is None


def test_collect_chat_kb_snippets(app):
    with app.app_context():
        from app.services.kb_chat.loader import clear_cache
        from app.services.kb_chat.snippets import collect_chat_kb_snippets

        clear_cache()
        snippets = collect_chat_kb_snippets("сколько стоит катер?")
        assert snippets
        joined = " ".join(snippets).lower()
        assert "10 000" in joined or "10000" in joined.replace(" ", "")


def test_fallback_what_to_bring_without_md(app, tmp_path, monkeypatch):
    with app.app_context():
        from app.services.kb_chat import loader as kb_loader
        from app.services.kb_chat.direct_replies import try_direct_what_to_bring_reply

        monkeypatch.setattr(kb_loader, "_chat_kb_root", lambda: tmp_path)
        kb_loader.clear_cache()
        reply = try_direct_what_to_bring_reply("что взять на катер?")
        assert reply is not None
        assert "катер" in reply.text.lower()
