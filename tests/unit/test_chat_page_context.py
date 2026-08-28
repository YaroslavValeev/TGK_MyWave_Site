"""Правила контекста страницы (зал / катер / разделы) для подсказок LLM."""

from app.services.chat_page_context import format_mw_chat_context_for_prompt, merge_chat_system_prompt


def test_gym_context_warns_about_indoor():
    block = format_mw_chat_context_for_prompt(
        {"entry": "services", "kind": "service", "id": "gym", "title": "Запись на тренировку (Зал)"}
    )
    assert "ЗАЛА" in block or "помещении" in block
    assert "купальник" in block.lower() or "солнцезащит" in block.lower()


def test_boat_context_allows_water_items():
    block = format_mw_chat_context_for_prompt(
        {"entry": "services", "kind": "service", "id": "boat", "title": "Запись на катер"}
    )
    assert "КАТЕРА" in block or "воды" in block


def test_shop_entry():
    block = format_mw_chat_context_for_prompt({"entry": "shop", "kind": "section", "title": "Товары на заказ"})
    assert "Товары" in block or "товар" in block.lower()


def test_merge_preserves_base_prompt():
    cfg = {"CHAT_SYSTEM_PROMPT": "BASE_PROMPT_UNIQUE"}
    merged = merge_chat_system_prompt(cfg, {"entry": "projects", "kind": "section", "title": "Проекты"})
    assert "BASE_PROMPT_UNIQUE" in merged
    assert "Проекты" in merged or "проект" in merged.lower()
