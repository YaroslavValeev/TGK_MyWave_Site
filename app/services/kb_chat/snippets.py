"""Collect KB v2 snippets for OpenAI prompt injection."""
from __future__ import annotations

from app.services.kb_chat.loader import load_index
from app.services.kb_chat.matcher import find_best_match, normalize_question
from app.services.kb_chat.routing import detect_service_location


def collect_chat_kb_snippets(
    prompt_lower: str,
    *,
    mw_chat_context: dict | None = None,
    max_snippets: int = 5,
) -> list[str]:
    snippets: list[str] = []
    seen: set[str] = set()

    loc = detect_service_location(prompt_lower, mw_chat_context)
    categories: list[str | None] = []
    if loc == "boat":
        categories.extend(["boat", "booking"])
    elif loc == "gym":
        categories.extend(["gym", "booking"])
    categories.append(None)

    for cat in categories:
        doc = find_best_match(prompt_lower, category=cat, min_score=15.0)
        if doc:
            key = doc.id
            if key not in seen:
                seen.add(key)
                snippets.append(doc.snippet_text())
        if len(snippets) >= max_snippets:
            break

    if len(snippets) < max_snippets:
        prompt_norm = normalize_question(prompt_lower)
        for doc in load_index():
            if doc.id in seen:
                continue
            hay = normalize_question(doc.short_answer + " " + " ".join(doc.triggers))
            if any(w in hay for w in prompt_norm.split() if len(w) > 4):
                seen.add(doc.id)
                snippets.append(doc.snippet_text())
            if len(snippets) >= max_snippets:
                break

    return snippets[:max_snippets]
