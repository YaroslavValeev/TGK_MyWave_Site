"""
Подсказки SEO/тегов/excerpt для Admin Blog (B4 UX).

Только эвристики по тексту поста + таксономия MyWave (услуги/проекты/события).
Не вызывает LLM. Не трогает final_posts.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.services.blog.display_text import plain_excerpt_for_display, plain_title_for_display

# Таксономия сайта: тег → ключевые слова в тексте (lower).
_TAG_KEYWORDS: List[tuple[str, tuple[str, ...]]] = [
    ("вейксёрфинг", ("вейксёрф", "вейксерф", "wakesurf", "wake surf")),
    ("вейкборд", ("вейкборд", "wakeboard", "wake board")),
    ("фойл", ("фойл", "foil", "foiling")),
    ("катер", ("катер", "boat", "сеанс", "слот")),
    ("тренировки", ("тренировк", "заняти", "инструктор", "коучинг", "coaching")),
    ("лагерь", ("лагерь", "кемп", "camp")),
    ("соревнования", ("соревнован", "контест", "contest", "чемпионат", "регистрац")),
    ("новости", ("новост", "news", "анонс")),
    ("события", ("событ", "event", "фестиваль", "festival")),
    ("онлайн", ("онлайн", "online", "разбор видео")),
    ("проекты", ("проект", "social", "миссия")),
]

_PLACEHOLDER_COVER_HINTS = (
    "place1logo",
    "/static/images/place1logo",
)


def _norm_space(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _is_blank(value: Optional[str]) -> bool:
    return not (value or "").strip()


def _is_weak_cover(url: Optional[str]) -> bool:
    s = (url or "").strip().lower()
    if not s or s in ("https://mywavewake.ru/static", "http://mywavewake.ru/static"):
        return True
    return any(h in s for h in _PLACEHOLDER_COVER_HINTS)


def suggest_tags(title: str, body: str, limit: int = 5) -> List[str]:
    blob = f"{title} {body}".lower()
    found: List[str] = []
    for tag, keys in _TAG_KEYWORDS:
        if any(k in blob for k in keys):
            found.append(tag)
        if len(found) >= limit:
            break
    if not found:
        found = ["новости", "вейксёрфинг"]
    return found


def suggest_seo_title(title: str, max_len: int = 70) -> str:
    t = plain_title_for_display(title, max_len=max_len)
    if not t:
        return "MyWave — новости вейксёрфинга"
    # Мягкий бренд-суффикс, если места хватает и бренда ещё нет.
    brand = " | MyWave"
    if "mywave" not in t.lower() and len(t) + len(brand) <= max_len:
        return t + brand
    return t


def suggest_meta(title: str, excerpt: str, body: str, limit: int = 160) -> str:
    src = excerpt or body or title
    text = plain_excerpt_for_display(src, limit=limit)
    if not text:
        return (
            "Новости и события MyWave: вейксёрфинг, тренировки, катер и проекты клуба."
        )
    return text


def build_card_suggestions(post: Dict[str, Any]) -> Dict[str, str]:
    """Предлагаемые значения карточки (всегда полный комплект)."""
    title = str(post.get("title") or "").strip()
    excerpt = str(post.get("excerpt") or "").strip()
    body = str(post.get("content_md") or "").strip()
    cover = str(post.get("cover_image_url") or post.get("image_url") or "").strip()

    tags = suggest_tags(title, body)
    seo_title = suggest_seo_title(title)
    meta = suggest_meta(title, excerpt, body)
    og_title = plain_title_for_display(title, max_len=70) or seo_title
    og_desc = meta

    if _is_weak_cover(cover):
        cover = ""

    return {
        "excerpt": plain_excerpt_for_display(excerpt or body or title, limit=220),
        "raw_tags": ", ".join(tags),
        "seo_title": seo_title,
        "meta_description": meta,
        "og_title": og_title,
        "og_description": og_desc,
        "cover_image_url": cover,
        "slug": str(post.get("slug") or "").strip(),
    }


def merge_empty_with_suggestions(
    current: Dict[str, Optional[str]],
    suggestions: Dict[str, str],
) -> Dict[str, str]:
    """
    Заполняет только пустые/слабые поля. Несуществующие ключи в current игнорирует.
    """
    out: Dict[str, str] = {}
    for key, suggested in suggestions.items():
        cur = current.get(key)
        if key == "cover_image_url":
            if _is_weak_cover(cur) and suggested:
                out[key] = suggested
            else:
                out[key] = (cur or "").strip() or suggested
            continue
        if _is_blank(cur):
            out[key] = suggested
        else:
            out[key] = _norm_space(str(cur))
    return out
