"""Match user questions to KB v2 documents."""
from __future__ import annotations

import re

from app.services.kb_chat.loader import load_index
from app.services.kb_chat.models import KBDocument

_PRIORITY_WEIGHT = {"high": 3, "normal": 2, "low": 1}


def _normalize(text: str) -> str:
    t = text.lower().strip()
    t = re.sub(r"[^\w\s?]", " ", t, flags=re.UNICODE)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def normalize_question(text: str) -> str:
    return _normalize(text)


def _score_doc(question_norm: str, doc: KBDocument) -> float:
    score = 0.0
    q_words = set(question_norm.split())

    for tq in doc.test_questions:
        tq_norm = _normalize(tq)
        if tq_norm == question_norm:
            score += 100.0
        elif tq_norm in question_norm or question_norm in tq_norm:
            score += 50.0
        else:
            overlap = len(q_words & set(tq_norm.split()))
            if overlap >= 2:
                score += overlap * 5.0

    for trigger in doc.triggers:
        trig_norm = _normalize(trigger)
        if trig_norm in question_norm:
            score += 20.0
        elif any(w in question_norm for w in trig_norm.split() if len(w) > 3):
            score += 5.0

    if doc.title:
        title_norm = _normalize(doc.title)
        if title_norm in question_norm:
            score += 15.0

    score += _PRIORITY_WEIGHT.get(doc.priority, 2)
    return score


def find_best_match(
    question: str,
    *,
    category: str | None = None,
    min_score: float = 25.0,
) -> KBDocument | None:
    question_norm = _normalize(question)
    if not question_norm:
        return None

    candidates = load_index()
    if category:
        candidates = [d for d in candidates if d.category.lower() == category.lower()]

    best: KBDocument | None = None
    best_score = 0.0
    for doc in candidates:
        s = _score_doc(question_norm, doc)
        if s > best_score:
            best_score = s
            best = doc

    if best and best_score >= min_score:
        return best
    return None


def get_by_stem(category: str, stem: str) -> KBDocument | None:
    for doc in load_index():
        if doc.category == category and doc.path.stem == stem:
            return doc
    return None
