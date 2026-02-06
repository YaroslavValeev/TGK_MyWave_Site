"""Utilities to fetch FAQ answers for AI tools and APIs."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Dict, List

FAQ_ENTRIES: List[Dict[str, str]] = [
    {
        "question": "Как записаться на тренировку по вейксерфингу?",
        "answer": "Выберите услугу, найдите свободный слот и подтвердите бронирование через форму или администратора.",
        "keywords": "записаться,тренировка,вейксерф",
    },
    {
        "question": "Что взять с собой на занятие?",
        "answer": "Возьмите купальник, полотенце и питьевую воду. Гидрокостюмы и доски предоставляет школа.",
        "keywords": "взять,занятие,экипировка,гидрокостюм",
    },
    {
        "question": "Можно ли перенести или отменить бронь?",
        "answer": "Сообщите нам не позднее чем за 12 часов до старта тренировки, и мы подберём новый слот или вернём оплату.",
        "keywords": "перенести,отмена,бронь",
    },
    {
        "question": "Сколько длится тренировка и сколько человек в группе?",
        "answer": "Стандартное занятие длится 60 минут, в группе не более 4 райдеров, чтобы сохранить персональное внимание.",
        "keywords": "длится,тренировка,сколько,человек,группа",
    },
]


def _score_entry(question: str, entry: Dict[str, str]) -> float:
    q = question.lower()
    keywords = [kw.strip() for kw in entry.get("keywords", "").split(",") if kw.strip()]
    keyword_hits = sum(1 for kw in keywords if kw and kw in q)
    similarity = SequenceMatcher(None, q, entry.get("question", "").lower()).ratio()
    return keyword_hits * 0.6 + similarity


def get_faq_answer(question: str) -> Dict[str, str]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")

    normalized = question.strip()
    best_entry = max(FAQ_ENTRIES, key=lambda entry: _score_entry(normalized, entry))
    return {
        "question": best_entry["question"],
        "answer": best_entry["answer"],
        "source": "faq",
    }
