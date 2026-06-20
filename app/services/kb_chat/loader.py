"""Load and cache KB v2 chat documents from knowledge_base/chat/."""
from __future__ import annotations

import os
from pathlib import Path

from flask import current_app

from app.services.kb_chat.models import KBDocument
from app.services.kb_chat.parser import parse_kb_file

_CACHE: dict[str, object] = {"mtime": 0.0, "docs": []}


def _chat_kb_root() -> Path:
    try:
        root = os.path.normpath(
            os.path.join(current_app.root_path, "..", "knowledge_base", "chat")
        )
    except RuntimeError:
        root = os.path.normpath(
            os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "knowledge_base", "chat"
            )
        )
    return Path(root)


def _dir_mtime(root: Path) -> float:
    if not root.is_dir():
        return 0.0
    latest = root.stat().st_mtime
    for path in root.rglob("*.md"):
        try:
            latest = max(latest, path.stat().st_mtime)
        except OSError:
            continue
    return latest


def load_index(*, force: bool = False) -> list[KBDocument]:
    root = _chat_kb_root()
    mtime = _dir_mtime(root)
    if not force and _CACHE["docs"] and _CACHE["mtime"] == mtime:
        return list(_CACHE["docs"])

    docs: list[KBDocument] = []
    if root.is_dir():
        for path in sorted(root.rglob("*.md")):
            if "_meta" in path.parts:
                continue
            doc = parse_kb_file(path)
            if doc and doc.short_answer:
                docs.append(doc)

    _CACHE["mtime"] = mtime
    _CACHE["docs"] = docs
    return list(docs)


def get_by_id(doc_id: str) -> KBDocument | None:
    for doc in load_index():
        if doc.id == doc_id:
            return doc
    return None


def list_by_category(category: str) -> list[KBDocument]:
    cat = category.lower().strip()
    return [d for d in load_index() if d.category.lower() == cat]


def clear_cache() -> None:
    _CACHE["mtime"] = 0.0
    _CACHE["docs"] = []
