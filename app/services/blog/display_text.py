"""
Единая нормализация текста для отображения на витрине (заголовки без сырого Markdown).

Используется в store, sync, publish — чтобы БД и Sheets давали тот же вид, что чтение в блог.
"""
from __future__ import annotations

import re
from typing import Optional

# Ведущий декоративный мусор (эмодзи / VS / ZWJ), не смысловой текст заголовка.
_LEADING_DECOR_RE = re.compile(
    r"^(?:"
    r"[\U0001F1E0-\U0001F1FF]"  # flags
    r"|[\U0001F300-\U0001FAFF]"  # symbols & pictographs
    r"|[\U00002600-\U000027BF]"  # misc symbols / dingbats
    r"|[\U0000FE00-\U0000FE0F]"  # variation selectors
    r"|[\U0000200D]"  # ZWJ
    r"|\s"
    r")+"
)


def plain_title_for_display(raw: Optional[str], max_len: int = 100) -> str:
    """
    Убирает типичный inline-Markdown из заголовка для h1 и <title>.
    Данные из Sheets могут содержать **…**, ссылки [текст](url), инлайн-код.
    Срезает ведущие эмодзи и мягко ограничивает длину для вкладки браузера.
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
    t = _LEADING_DECOR_RE.sub("", t)
    t = re.sub(r"\s+", " ", t).strip()
    if max_len and len(t) > max_len:
        clipped = t[:max_len].rsplit(" ", 1)[0]
        t = (clipped or t[:max_len]).rstrip(".,;:—- ") + "…"
    return t


def plain_excerpt_for_display(raw: Optional[str], limit: int = 220) -> str:
    """Короткий превью-текст для карточек блога без сырого Markdown."""
    if not raw:
        return ""
    text = str(raw).strip()
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    clipped = text[:limit].rsplit(" ", 1)[0]
    return (clipped or text[:limit]).strip() + "…"
