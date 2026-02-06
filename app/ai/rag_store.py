from __future__ import annotations

from typing import List
import json
import os
import logging
from dataclasses import dataclass, asdict
from math import sqrt

from flask import current_app

logger = logging.getLogger(__name__)


@dataclass
class RAGDocument:
    id: str
    source: str  # 'site', 'safari', 'challenge', ...
    title: str
    text: str
    tags: List[str]
    embedding: List[float]


class RAGStore:
    """Файловое RAG-хранилище (JSON) без внешней БД."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.docs: List[RAGDocument] = []

    def load(self) -> None:
        if not os.path.exists(self.path):
            logger.info("[RAG] Index not found at %s, starting empty", self.path)
            self.docs = []
            return
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.docs = [RAGDocument(**d) for d in (data or {}).get("docs", [])]
        logger.info("[RAG] Loaded %s docs from %s", len(self.docs), self.path)

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(
                {"docs": [asdict(d) for d in self.docs]},
                f,
                ensure_ascii=False,
                indent=2,
            )
        logger.info("[RAG] Saved %s docs to %s", len(self.docs), self.path)

    def add_docs(self, docs: List[RAGDocument], replace: bool = False) -> None:
        if replace:
            self.docs = docs
        else:
            self.docs.extend(docs)
        self.save()

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[RAGDocument]:
        def cosine(a, b):
            if not a or not b:
                return 0.0
            s = sum(x * y for x, y in zip(a, b))
            na = sqrt(sum(x * x for x in a))
            nb = sqrt(sum(y * y for y in b))
            return s / (na * nb) if na and nb else 0.0

        scored = [(cosine(query_embedding, d.embedding), d) for d in self.docs]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [d for score, d in scored[:top_k]]


def get_rag_store() -> RAGStore:
    path = current_app.config["RAG_INDEX_PATH"]
    store = RAGStore(path)
    store.load()
    return store
