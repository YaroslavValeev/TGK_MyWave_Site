"""
Единая нормализация текста для отображения на витрине (заголовки без сырого Markdown).

Используется в store, sync, publish — чтобы БД и Sheets давали тот же вид, что чтение в блог.
"""
from __future__ import annotations

import re
from typing import Optional


def plain_title_for_display(raw: Optional[str]) -> str:
    """
    Убирает типичный inline-Markdown из заголовка для h1 и <title>.
    Данные из Sheets могут содержать **…**, ссылки [текст](url), инлайн-код.
    """
    if not raw:
        return ""
    t = str(raw).strip()
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)
    for _ in range(4):
        prev = t
        t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
        t = re.sub(r"__([^_]+)__", r"\1", t)
        if t == prev:
            break
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", t)
    t = re.sub(r"`([^`]+)`", r"\1", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t
