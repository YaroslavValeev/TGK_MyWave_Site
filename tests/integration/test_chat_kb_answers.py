"""Integration tests: chat API answers from Knowledge Base v2 (20-question matrix)."""
from __future__ import annotations

import pytest

# Wave 1 acceptance matrix (ТЗ §8 + §12)
KB_ANSWER_CASES = [
    pytest.param(
        "Что взять на катер?",
        {"must_contain": ["купальник", "полотенц"], "must_not_contain": ["вам нужна запись в зал или на катер"]},
        id="01_boat_what_to_bring",
    ),
    pytest.param(
        "Что взять?",
        {"must_contain": ["зал", "катер"], "must_not_contain": []},
        id="02_what_to_bring_disambiguation",
    ),
    pytest.param(
        "Сколько стоит катер?",
        {"must_contain": ["10 000", "25"], "must_not_contain": []},
        id="03_boat_price",
    ),
    pytest.param(
        "Сколько стоит тренировка в зале?",
        {"must_contain": ["3 500", "1,5"], "must_not_contain": []},
        id="04_gym_price",
    ),
    pytest.param(
        "Как записаться?",
        {"must_contain": ["катер", "зал"], "must_not_contain": [], "expect_suggestions": True},
        id="05_booking_disambiguation",
    ),
    pytest.param(
        "Можно новичку на катер?",
        {"must_contain": ["нович", "25"], "must_not_contain": []},
        id="06_boat_beginner",
    ),
    pytest.param(
        "Сколько длится сет?",
        {"must_contain": ["25"], "must_not_contain": []},
        id="07_boat_set_duration",
    ),
    pytest.param(
        "Что входит в сет?",
        {"must_contain": ["25", "тренер"], "must_not_contain": []},
        id="08_boat_set_includes",
    ),
    pytest.param(
        "Нужен ли гидрокостюм?",
        {"must_contain": ["гидрокостюм"], "must_not_contain": []},
        id="09_wetsuit",
    ),
    pytest.param(
        "Можно ребёнку на катер?",
        {"must_contain": ["реб", "менеджер"], "must_not_contain": []},
        id="10_boat_children",
    ),
    pytest.param(
        "Что взять в зал?",
        {"must_contain": ["одежд", "полотенц"], "must_not_contain": ["вам нужна запись в зал или на катер"]},
        id="11_gym_what_to_bring",
    ),
    pytest.param(
        "Сколько длится тренировка в зале?",
        {"must_contain": ["1,5"], "must_not_contain": []},
        id="12_gym_duration",
    ),
    pytest.param(
        "Чем зал помогает вейксерфу?",
        {"must_contain": ["баланс", "координ"], "must_not_contain": []},
        id="13_gym_wakesurf_help",
    ),
    pytest.param(
        "Можно без опыта в зале?",
        {"must_contain": ["можно", "опыт"], "must_not_contain": []},
        id="14_gym_no_experience",
    ),
    pytest.param(
        "Есть ли противопоказания для зала?",
        {"must_contain": ["противопоказ", "менеджер"], "must_not_contain": []},
        id="15_gym_contraindications",
    ),
    pytest.param(
        "Как отменить запись?",
        {"must_contain": ["отмен", "менеджер"], "must_not_contain": []},
        id="16_booking_cancel",
    ),
    pytest.param(
        "Как оплатить занятие?",
        {"must_contain": ["оплат", "менеджер"], "must_not_contain": []},
        id="17_booking_payment",
    ),
    pytest.param(
        "Что делать, если нет нужного времени?",
        {"must_contain": ["менеджер"], "must_not_contain": []},
        id="18_no_slots",
    ),
    pytest.param(
        "Какой телефон MyWave?",
        {"must_contain": ["916", "011"], "must_not_contain": []},
        id="19_contacts_phone",
    ),
    pytest.param(
        "Как связаться с менеджером?",
        {"must_contain": ["telegram", "телефон"], "must_not_contain": []},
        id="20_contacts_manager",
    ),
]


@pytest.mark.parametrize("message,expectations", KB_ANSWER_CASES)
def test_chat_kb_direct_answers(client, message, expectations):
    response = client.post(
        "/chat/api",
        json={"message": message},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json() or {}
    text = (data.get("response") or "").lower()

    for token in expectations.get("must_contain", []):
        assert token.lower() in text, f"expected '{token}' in response for: {message!r}"

    for token in expectations.get("must_not_contain", []):
        assert token.lower() not in text, f"unexpected '{token}' in response for: {message!r}"

    if expectations.get("expect_suggestions"):
        suggestions = data.get("suggestions") or []
        assert suggestions, f"expected suggestions for: {message!r}"
        joined = " ".join(suggestions).lower()
        assert "катер" in joined and "зал" in joined
