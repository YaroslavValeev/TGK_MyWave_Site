from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Optional

from flask import current_app

from app.modules.sheets import get_all_records


@dataclass(frozen=True)
class HomepageReview:
    name: str
    text: str
    photo_static_path: Optional[str] = None


_NAME_TO_PHOTO: dict[str, str] = {
    "эля веснина": "images/students/Elya_Vesnina.jpg",
    "юля елупова": "images/students/Elupova.jpg",
    "юлия елупова": "images/students/Elupova.jpg",
    "алина лапина": "images/students/Alya_Lapina.jpg",
    "али лапина": "images/students/Alya_Lapina.jpg",
}


_FALLBACK_REVIEWS: list[HomepageReview] = [
    HomepageReview(
        name="Эля Веснина",
        text="Очень понравились тренировки! Тренер — супер!",
        photo_static_path=_NAME_TO_PHOTO.get("эля веснина"),
    ),
    HomepageReview(
        name="Юля Елупова",
        text="Было весело и эффективно, всем советую!",
        photo_static_path=_NAME_TO_PHOTO.get("юля елупова"),
    ),
    HomepageReview(
        name="Алина Лапина",
        text="Прекрасный подход к детям и взрослым!",
        photo_static_path=_NAME_TO_PHOTO.get("алина лапина"),
    ),
]


def _parse_datetime(value: str) -> Optional[datetime]:
    value = (value or "").strip()
    if not value:
        return None

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y %H:%M:%S", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            continue
    return None


def _clean_text(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    if (text.startswith('"') and text.endswith('"')) or (
        text.startswith("“") and text.endswith("”")
    ):
        text = text[1:-1].strip()
    return text


def _pick_first(mapping: dict[str, Any], keys: Iterable[str]) -> str:
    for key in keys:
        value = mapping.get(key)
        if value is None:
            continue
        value_str = str(value).strip()
        if value_str:
            return value_str
    return ""


def _normalize_photo_static_path(value: str) -> Optional[str]:
    """Normalize a user-provided photo path from Sheets to Flask `url_for('static', filename=...)`.

    Supported formats in Sheets:
    - images/students/Foo.jpg
    - /static/images/students/Foo.jpg
    - static/images/students/Foo.jpg
    """
    raw = (value or "").strip()
    if not raw:
        return None

    lowered = raw.lower()
    if lowered.startswith("http://") or lowered.startswith("https://"):
        # Keep homepage CSP/simple setup: only support static file paths by default.
        return None

    path = raw.replace("\\", "/").strip()
    if ".." in path:
        return None

    if path.startswith("/"):
        path = path[1:]
    if path.startswith("static/"):
        path = path[len("static/") :]
    if path.startswith("/static/"):
        path = path[len("/static/") :]

    # Common user input: "/images/..." (missing "static" prefix)
    if path.startswith("images/"):
        return path
    if path.startswith("/images/"):
        return path[1:]

    return path or None


def _photo_by_name(name: str) -> Optional[str]:
    key = (name or "").strip().lower()
    return _NAME_TO_PHOTO.get(key)


def get_homepage_reviews(max_items: int = 20) -> list[HomepageReview]:
    """Return reviews for the home page.

    Source of truth: Google Sheet `Feedback_Reviews` (same one used by /reviews).
    Fallback: built-in 3 sample reviews with photos.
    """
    spreadsheet_id = current_app.config.get("SPREADSHEET_ID")
    if not spreadsheet_id:
        return _FALLBACK_REVIEWS

    try:
        try:
            import eventlet

            with eventlet.Timeout(3, False):
                raw_records = get_all_records("Feedback_Reviews")
            if raw_records is None:
                raise TimeoutError("Sheets request timed out")
        except Exception:
            raw_records = get_all_records("Feedback_Reviews")
    except Exception as exc:
        current_app.logger.warning(
            "Failed to load Feedback_Reviews from Sheets: %s", exc
        )
        return _FALLBACK_REVIEWS

    normalized: list[tuple[Optional[datetime], HomepageReview]] = []
    for rec in raw_records or []:
        if not isinstance(rec, dict):
            continue

        name = _pick_first(
            rec, ("name", "author", "username", "student", "client_name")
        ).strip()
        if not name:
            name = "Ученик"

        text = _clean_text(_pick_first(rec, ("comment", "text", "review", "message")))
        if not text:
            continue

        created_at_raw = _pick_first(rec, ("created_at", "created", "date"))
        created_at = _parse_datetime(created_at_raw)

        photo_from_sheet = _pick_first(
            rec, ("photo", "photo_path", "photo_static_path", "avatar", "image")
        )
        photo = _normalize_photo_static_path(photo_from_sheet) or _photo_by_name(name)
        normalized.append(
            (created_at, HomepageReview(name=name, text=text, photo_static_path=photo))
        )

    if not normalized:
        return _FALLBACK_REVIEWS

    normalized.sort(key=lambda item: item[0] or datetime.min, reverse=True)
    return [item[1] for item in normalized[:max_items]]
