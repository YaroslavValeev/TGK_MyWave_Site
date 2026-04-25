"""
HTTP-smoke раздела «Чат» без Playwright (стабильно в CI при live_server).

Полные сценарии виджета (приветствие, мок API) — в test_chat_section.py
при E2E_PLAYWRIGHT=1 или вручную по docs/CHAT_RUNTIME_AND_RELEASE.md.
"""
import pytest
import requests


@pytest.mark.e2e
def test_chat_page_returns_widget_markup(live_server):
    r = requests.get(live_server + "/chat/", timeout=30)
    assert r.status_code == 200
    html = r.text
    assert 'id="chat-toggle"' in html
    assert 'id="chat-widget"' in html
    assert 'id="chat-form"' in html
    assert 'id="chat-input"' in html
    assert "/static/js/chat.js" in html


@pytest.mark.e2e
def test_chat_page_has_autopen_script(live_server):
    r = requests.get(live_server + "/chat/", timeout=30)
    assert r.status_code == 200
    assert "openChatWidget" in r.text or "chat-toggle" in r.text
