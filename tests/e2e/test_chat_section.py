"""
E2E только для раздела «Чат»: старт с /chat/, без зависимости от главной.

Сценарии с моком POST /chat/api через Playwright route (без реального OpenAI).

Включение: E2E_PLAYWRIGHT=1. Иначе пропуск: live_server + eventlet + Chromium на части
окружений дают таймауты; для релиза используйте test_chat_section_http.py и ручной смоук.
"""
import json
import os
import time

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("E2E_PLAYWRIGHT", "").strip().lower() not in ("1", "true", "yes"),
    reason="Задайте E2E_PLAYWRIGHT=1 для браузерных сценариев или используйте HTTP-smoke / ручной чеклист",
)


@pytest.fixture
def _chat_api_mock_factory():
    def make(body: dict, status: int = 200):
        def handle(route):
            if route.request.method == "POST" and "/chat/api" in route.request.url:
                route.fulfill(
                    status=status,
                    content_type="application/json",
                    body=json.dumps(body, ensure_ascii=False),
                )
            else:
                route.continue_()

        return handle

    return make


@pytest.mark.e2e
def test_chat_widget_welcome_and_message_mocked(live_server, page, _chat_api_mock_factory):
    page.add_init_script("localStorage.removeItem('mw_chat_welcome_v1');")
    page.route("**/chat/api", _chat_api_mock_factory({"response": "Мок-ответ OK", "status": "success"}))
    page.goto(live_server + "/chat/", wait_until="domcontentloaded", timeout=90000)

    # /chat/ автооткрывает виджет; приветствие один раз
    page.wait_for_selector("#chat-messages .message", timeout=10000)
    welcome_text = page.locator("#chat-messages").inner_text()
    assert "вейксерф" in welcome_text.lower() or "запис" in welcome_text.lower()

    page.locator("#chat-input").fill("Обычный вопрос")
    page.locator("#chat-form").locator('button[type="submit"]').click()
    page.wait_for_function(
        "() => document.getElementById('chat-messages')?.innerText.includes('Мок-ответ')",
        timeout=8000,
    )


@pytest.mark.e2e
def test_chat_booking_shape_mocked(live_server, page, _chat_api_mock_factory):
    page.add_init_script("localStorage.removeItem('mw_chat_welcome_v1');")
    booking_body = {
        "response": "На какую дату хотите записаться?",
        "state": {"step": "ask_date"},
        "suggestions": ["сегодня", "завтра"],
    }
    page.route("**/chat/api", _chat_api_mock_factory(booking_body))
    page.goto(live_server + "/chat/", wait_until="domcontentloaded", timeout=90000)
    page.wait_for_selector("#chat-input", state="visible", timeout=10000)
    page.locator("#chat-input").fill("хочу записаться завтра")
    page.locator("#chat-form").locator('button[type="submit"]').click()
    page.wait_for_function(
        "() => document.getElementById('chat-messages')?.innerText.includes('дат')",
        timeout=8000,
    )
    assert page.locator("#chat-suggestions .suggestion-chip").count() >= 1


@pytest.mark.e2e
def test_chat_rate_limit_ui_mocked(live_server, page, _chat_api_mock_factory):
    page.add_init_script("localStorage.removeItem('mw_chat_welcome_v1');")
    page.route(
        "**/chat/api",
        _chat_api_mock_factory(
            {"response": "Слишком много сообщений.", "status": "rate_limited"},
            status=429,
        ),
    )
    page.goto(live_server + "/chat/", wait_until="domcontentloaded", timeout=90000)
    page.wait_for_selector("#chat-input", state="visible", timeout=10000)
    page.locator("#chat-input").fill("тест лимита")
    page.locator("#chat-form").locator('button[type="submit"]').click()
    page.wait_for_function(
        "() => document.getElementById('chat-messages')?.innerText.toLowerCase().includes('много')",
        timeout=8000,
    )


@pytest.mark.e2e
def test_chat_error_status_200_mocked(live_server, page, _chat_api_mock_factory):
    page.add_init_script("localStorage.removeItem('mw_chat_welcome_v1');")
    page.route(
        "**/chat/api",
        _chat_api_mock_factory(
            {"response": "Извините, AI временно недоступен.", "status": "error"},
            status=200,
        ),
    )
    page.goto(live_server + "/chat/", wait_until="domcontentloaded", timeout=90000)
    page.wait_for_selector("#chat-input", state="visible", timeout=10000)
    page.locator("#chat-input").fill("ошибка")
    page.locator("#chat-form").locator('button[type="submit"]').click()
    page.wait_for_function(
        "() => document.getElementById('chat-messages')?.innerText.includes('недоступен')",
        timeout=8000,
    )


@pytest.mark.e2e
def test_chat_no_severe_console_errors(live_server, page, _chat_api_mock_factory):
    errors = []

    def on_console(msg):
        if msg.type == "error":
            text = (msg.text or "").lower()
            noise = (
                "favicon",
                "socket.io",
                "websocket",
                "failed to load",
                "net::err",
                "content security policy",
            )
            if any(n in text for n in noise):
                return
            errors.append(msg.text)

    page.on("console", on_console)
    page.add_init_script("localStorage.removeItem('mw_chat_welcome_v1');")
    page.route("**/chat/api", _chat_api_mock_factory({"response": "OK", "status": "success"}))
    page.goto(live_server + "/chat/", wait_until="domcontentloaded", timeout=90000)
    time.sleep(1.5)
    page.locator("#chat-input").fill("ping")
    page.locator("#chat-form").locator('button[type="submit"]').click()
    time.sleep(2)
    assert not errors, f"console errors: {errors}"
