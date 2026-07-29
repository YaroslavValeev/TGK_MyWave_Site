"""
Подсказки SEO/тегов/excerpt + SEO quality checklist для Admin Blog (B4.2 soft).

Только эвристики (без LLM). Не трогает final_posts / медиа-upload.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.services.blog.display_text import plain_excerpt_for_display, plain_title_for_display

# Таксономия MyWave: услуги / продукты / проекты / индустрия.
_TAG_KEYWORDS: List[tuple[str, tuple[str, ...]]] = [
    # Услуги клуба
    ("вейксёрфинг", ("вейксёрф", "вейксерф", "wakesurf", "wake surf")),
    ("вейкборд", ("вейкборд", "wakeboard", "wake board")),
    ("катер", ("катер", "boat", "сеанс", "слот", "запись на воду", "причал")),
    ("тренировки", ("тренировк", "заняти", "инструктор", "занятие с тренером")),
    ("онлайн-коучинг", ("онлайн", "online", "коучинг", "coaching", "разбор видео", "видеоразбор")),
    ("лагерь", ("лагерь", "кемп", "camp", "выезд")),
    # Проекты / бренд
    ("social-mission", ("social", "миссия", "адаптивн", "дети с", "инклюз")),
    ("mywave", ("mywave", "майвейв", "клуб mywave")),
    # Контент / индустрия
    ("фойл", ("фойл", "foil", "foiling")),
    ("соревнования", ("соревнован", "контест", "contest", "чемпионат", "регистрац", "старт")),
    ("события", ("событ", "event", "фестиваль", "festival", "meetup")),
    ("новости", ("новост", "news", "анонс", "обзор")),
    ("снаряжение", ("снаряжен", "доска", "креплен", "жилет", "товар", "экипиров")),
]

_PLACEHOLDER_COVER_HINTS = (
    "place1logo",
    "/static/images/place1logo",
)

_CTA_BY_SIGNAL: List[tuple[tuple[str, ...], str]] = [
    (("катер", "boat", "сеанс", "слот"), "Запись на катер — на сайте MyWave."),
    (("онлайн", "коучинг", "разбор видео"), "Онлайн-коучинг и разбор видео — в разделе MyWave."),
    (("лагерь", "кемп", "camp"), "Лагеря и выезды — в разделе Camp на сайте MyWave."),
    (("тренировк", "инструктор"), "Тренировки с инструктором — на сайте MyWave."),
]


def _norm_space(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _is_blank(value: Optional[str]) -> bool:
    return not (value or "").strip()


def _is_weak_cover(url: Optional[str]) -> bool:
    s = (url or "").strip().lower()
    if not s or s in ("https://mywavewake.ru/static", "http://mywavewake.ru/static"):
        return True
    return any(h in s for h in _PLACEHOLDER_COVER_HINTS)


def _clip_words(text: str, max_len: int) -> str:
    t = _norm_space(text)
    if len(t) <= max_len:
        return t
    clipped = t[:max_len].rsplit(" ", 1)[0]
    return (clipped or t[:max_len]).rstrip(".,;:—- ")


def suggest_tags(title: str, body: str, limit: int = 5) -> List[str]:
    blob = f"{title} {body}".lower()
    found: List[str] = []
    for tag, keys in _TAG_KEYWORDS:
        if any(k in blob for k in keys):
            found.append(tag)
        if len(found) >= limit:
            break
    if not found:
        found = ["новости", "вейксёрфинг", "mywave"]
    return found


def suggest_seo_title(title: str, max_len: int = 60) -> str:
    """SERP-ориентир ~50–60 символов, бренд в конце если влезает."""
    t = plain_title_for_display(title, max_len=0)
    t = _clip_words(t, max_len=max_len - 10)  # запас под бренд
    if not t:
        return "MyWave — вейксёрфинг и тренировки"
    brand = " | MyWave"
    if "mywave" not in t.lower() and len(t) + len(brand) <= max_len:
        return t + brand
    return _clip_words(t, max_len)


def _service_cta(title: str, body: str) -> str:
    blob = f"{title} {body}".lower()
    for keys, cta in _CTA_BY_SIGNAL:
        if any(k in blob for k in keys):
            return cta
    return "Подробнее — на сайте MyWave: тренировки, катер и проекты."


def suggest_meta(title: str, excerpt: str, body: str, limit: int = 155) -> str:
    src = excerpt or body or title
    base = plain_excerpt_for_display(src, limit=limit - 55)
    cta = _service_cta(title, body)
    if not base:
        return _clip_words(
            f"Новости MyWave: вейксёрфинг, тренировки и катер. {cta}",
            limit,
        )
    # Не дублировать CTA, если уже есть «mywave» в конце.
    if "mywave" in base.lower():
        return _clip_words(base, limit)
    joined = f"{base.rstrip('.')} — {cta}"
    return _clip_words(joined, limit)


def build_card_suggestions(post: Dict[str, Any]) -> Dict[str, str]:
    """Предлагаемые значения карточки (всегда полный комплект)."""
    title = str(post.get("title") or "").strip()
    excerpt = str(post.get("excerpt") or "").strip()
    body = str(post.get("content_md") or "").strip()
    cover = str(post.get("cover_image_url") or post.get("image_url") or "").strip()

    tags = suggest_tags(title, body)
    seo_title = suggest_seo_title(title)
    meta = suggest_meta(title, excerpt, body)
    og_title = _clip_words(plain_title_for_display(title, max_len=0) or seo_title, 70)
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
    """Заполняет только пустые/слабые поля."""
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


@dataclass
class SeoCheck:
    level: str  # ok | warn | fail
    code: str
    message: str


def evaluate_seo_card(fields: Dict[str, Any]) -> Tuple[int, List[SeoCheck]]:
    """
    Лёгкий чеклист качества карточки (не полноценный SEO-аудит).
    Возвращает score 0–100 и список проверок.
    """
    checks: List[SeoCheck] = []
    seo_title = _norm_space(str(fields.get("seo_title") or ""))
    meta = _norm_space(str(fields.get("meta_description") or ""))
    tags_raw = str(fields.get("raw_tags") or "")
    tags = [t.strip() for t in re.split(r"[,;]", tags_raw) if t.strip()]
    cover = str(fields.get("cover_image_url") or "")
    excerpt = _norm_space(str(fields.get("excerpt") or ""))
    slug = _norm_space(str(fields.get("slug") or ""))
    og_title = _norm_space(str(fields.get("og_title") or ""))

    def add(level: str, code: str, message: str) -> None:
        checks.append(SeoCheck(level=level, code=code, message=message))

    if not seo_title:
        add("fail", "seo_title_empty", "seo_title пустой")
    elif len(seo_title) > 60:
        add("warn", "seo_title_long", f"seo_title длинный ({len(seo_title)} > 60) — в выдаче обрежется")
    elif len(seo_title) < 25:
        add("warn", "seo_title_short", "seo_title коротковат — добавьте смысл/бренд")
    else:
        add("ok", "seo_title_ok", f"seo_title длина {len(seo_title)} — ок")

    if not meta:
        add("fail", "meta_empty", "meta_description пустой")
    elif len(meta) < 70:
        add("warn", "meta_short", f"meta короткий ({len(meta)} < 70)")
    elif len(meta) > 160:
        add("warn", "meta_long", f"meta длинный ({len(meta)} > 160)")
    else:
        add("ok", "meta_ok", f"meta длина {len(meta)} — ок")

    if len(tags) < 2:
        add("fail", "tags_few", "Нужно ≥2 тега (услуги/тема/событие)")
    elif len(tags) > 6:
        add("warn", "tags_many", "Слишком много тегов — оставьте 2–5 сильных")
    else:
        add("ok", "tags_ok", f"тегов: {len(tags)}")

    if _is_weak_cover(cover):
        add("fail", "cover_weak", "Нет нормальной обложки (Place1Logo / пусто / битый URL)")
    else:
        add("ok", "cover_ok", "обложка задана")

    if slug and (len(slug) > 80 or not slug.replace("-", "").replace("_", "").isalnum()):
        add("warn", "slug_awkward", "slug длинный или не ASCII — лучше короткий латинице")
    elif slug:
        add("ok", "slug_ok", "slug выглядит приемлемо")

    if excerpt and seo_title and excerpt.lower() == seo_title.lower():
        add("warn", "excerpt_dup", "excerpt совпадает с title — добавьте лид/пользу")

    if og_title and seo_title and og_title == seo_title:
        add("ok", "og_aligned", "og_title совпадает с seo_title")
    elif not og_title:
        add("warn", "og_title_empty", "og_title пустой")

    # Score: fail -25, warn -10, ok +8 (cap 100)
    score = 50
    for c in checks:
        if c.level == "fail":
            score -= 25
        elif c.level == "warn":
            score -= 10
        else:
            score += 8
    score = max(0, min(100, score))
    return score, checks


def seo_checklist_for_template(fields: Dict[str, Any]) -> Dict[str, Any]:
    score, checks = evaluate_seo_card(fields)
    fails = sum(1 for c in checks if c.level == "fail")
    warns = sum(1 for c in checks if c.level == "warn")
    return {
        "score": score,
        "fails": fails,
        "warns": warns,
        "checks": checks,
        "ready": fails == 0,
        "label": (
            "готово к сохранению"
            if fails == 0 and warns <= 1
            else ("есть замечания" if fails == 0 else "нужны правки")
        ),
    }
