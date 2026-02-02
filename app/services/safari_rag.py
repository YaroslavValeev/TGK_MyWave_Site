"""
Simple RAG helper for Safari content.

Provides retrieval functions over `Document` content and a small prompt builder.
This is intentionally lightweight and deterministic (no external calls).
"""

from typing import List, Dict
from sqlalchemy import or_
from app.database.models import Document


def retrieve_by_keyword(keyword: str, k: int = 3) -> List[Dict]:
    """Return top-k documents matching keyword in title or content.

    This uses a simple SQL LIKE match; in production replace with proper vector search.
    """
    if not keyword:
        return []

    like = f"%{keyword}%"
    docs = (
        Document.query.filter(
            or_(Document.title.ilike(like), Document.content.ilike(like))
        )
        .limit(k)
        .all()
    )

    results = []
    for d in docs:
        results.append(
            {"id": d.id, "title": d.title, "content": d.content, "meta": d.meta or {}}
        )
    return results


def build_rag_prompt(user_question: str, contexts: List[Dict]) -> str:
    """Build a RAG prompt by concatenating top contexts and the question.

    Keep prompt short and clear for downstream LLM usage.
    """
    parts = [
        f"Context {i+1}: {c.get('title','')}. {c.get('content','')[:600]}"
        for i, c in enumerate(contexts)
    ]
    ctx_block = "\n\n".join(parts)
    prompt = f"You are a helpful assistant for WakeSurf Safari. Use the following contexts to answer the question.\n\n{ctx_block}\n\nQuestion: {user_question}\n\nAnswer concisely:"
    return prompt
