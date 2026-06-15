"""
Гибридный store для блога: Sheets как источник истины, БД как резерв/кэш.

Канонический контракт витрины и mapping legacy-полей:
docs/architecture/BLOG_CANONICAL_MAPPING.md

Правило «publishable» для строк Sheets (контракт v1): docs/BLOG_CONTRACT_v1.md — реализация: app/services/blog/publishability.py
"""
import json
import os
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from flask import current_app

from app.database.models import BlogPost, db
from app.modules.logger import get_logger
from app.services.parser_news_sheet import fetch_parser_news_rows
from app.services.google import get_google_services
from app.services.parser_news_sheet import resolve_parser_source
from app.services.blog.render import safe_render_markdown
from app.services.blog.display_text import plain_title_for_display
from app.services.blog.sync import (
    _safe_dt,
    _slugify,
    _parse_tags,
)
from app.services.blog.publishability import (
    DB_PUBLISHABLE_STATUS_VALUES,
    is_publishable_blog_post_record,
    is_publishable_row,
)
from app.services.blog.video_embed import attach_video_display_fields

logger = get_logger(__name__)

# Кэш для Sheets данных (TTL 60-180 сек)
_cache: Dict[str, Dict] = {"sheets_data": {"ts": 0, "data": []}}

# Текст карточек списка/главной, если после очистки не осталось содержимого
FALLBACK_BLOG_CARD_EXCERPT = "Описание публикации скоро появится."

# Хвосты тестовых записей вида site_p0_test_… / (site_p0_test_…)
_RE_SITE_TEST_TOKEN = re.compile(
    r"\(?\s*site_p\d+_test_[A-Za-z0-9_]+\s*\)?",
    re.IGNORECASE,
)


def invalidate_blog_sheets_cache() -> None:
    """Сбросить in-memory кэш постов из Sheets (следующий запрос перечитает таблицу)."""
    _cache["sheets_data"] = {"ts": 0, "data": []}


def _clip_for_log(val: Optional[str], limit: int = 280) -> str:
    s = (str(val) if val is not None else "").strip()
    if len(s) <= limit:
        return s
    return s[: limit - 1] + "…"


def _blog_excerpt_trace_enabled() -> bool:
    """Временная диагностика: slug + исходные поля excerpt и итог после нормализации."""
    if os.getenv("BLOG_DEBUG_EXCERPT_TRACE", "").strip().lower() in ("1", "true", "yes", "y"):
        return True
    try:
        return bool(current_app and current_app.config.get("BLOG_DEBUG_EXCERPT_TRACE"))
    except RuntimeError:
        return False


_RAW_FEED_HEADER_KEYS_ALL = [
    "id",
    "source_type",
    "source_name",
    "source_url",
    "created_at",
    "ingest_status",
    "raw_title",
    "final_posts",
    "summary",
    "status",
    "slug",
    "published_at",
]

_RAW_FEED_HEADER_KEYS_DENSE_ORDER = [
    "id",
    "source_type",
    "source_name",
    "source_url",
    "created_at",
    "ingest_status",
    "raw_title",
]


def _normalize_header_cell(cell: object) -> str:
    """Нормализует значение ячейки под сравнение с именами колонок."""
    s = "" if cell is None else str(cell)
    s = s.replace("\ufeff", "")  # BOM на всякий случай
    return s.strip().lower()


def _detect_parser_header_row_with_trace(rows: list[list[str]]) -> tuple[int | None, dict]:
    """
    Строгий detection строки заголовков для raw_feed (ParserNews).

    Важно: у raw_feed встречается "hybrid row":
    часть ячейки может содержать данные постов, а в хвосте — названия полей.
    Такая строка должна отклоняться, если содержит подозрительно "контентные" значения.
    """

    best: tuple[int, dict] | None = None

    for idx, row in enumerate(rows):
        # Грубая эвристика "не похоже на заголовки": слишком много длинных/контентных ячеек.
        normalized_cells: list[tuple[int, str]] = []
        raw_cells: list[str] = []
        raw_by_idx: dict[int, str] = {}
        for col_i, cell in enumerate(row):
            if cell is None:
                continue
            raw_s = str(cell).strip()
            if not raw_s:
                continue
            raw_cells.append(raw_s)
            raw_by_idx[col_i] = raw_s
            n = _normalize_header_cell(cell)
            normalized_cells.append((col_i, n))

        non_empty = len(raw_cells)
        if non_empty == 0:
            continue

        long_cells = [s for s in raw_cells if len(s) > 40]
        very_long_cells = [s for s in raw_cells if len(s) > 120]
        contains_markdown = any(s.startswith("#") or "```" in s for s in raw_cells)
        contains_http = any("http://" in s.lower() or "https://" in s.lower() for s in raw_cells)
        contains_known_test_tokens = any("missing row_number" in s.lower() for s in raw_cells)

        if (
            very_long_cells
            or contains_markdown
            or contains_http
            or contains_known_test_tokens
            or (len(long_cells) >= 3 and (len(long_cells) / max(1, non_empty)) > 0.10)
        ):
            # Отбрасываем: заголовки не должны содержать реальный контент.
            continue

        positions_all: dict[str, int] = {}
        for col_i, token in normalized_cells:
            if token in _RAW_FEED_HEADER_KEYS_ALL:
                positions_all.setdefault(token, col_i)

        matched_all = [k for k in _RAW_FEED_HEADER_KEYS_ALL if k in positions_all]
        if len(matched_all) < 8:
            continue

        # Плотность по ключевым колонкам
        dense_present = [k for k in _RAW_FEED_HEADER_KEYS_DENSE_ORDER if k in positions_all]
        if len(dense_present) < 4:
            continue

        dense_indices = [positions_all[k] for k in dense_present]
        span = max(dense_indices) - min(dense_indices)
        if span > 35:
            continue

        # Доп. защита от "hybrid row":
        # если вне плотного range dense-колонок есть много длинных/контентных значений —
        # строка не должна считаться заголовком.
        header_start = min(dense_indices)
        header_end = max(dense_indices)
        suspicious_outside = 0
        for col_i, raw_s in raw_by_idx.items():
            if header_start <= col_i <= header_end:
                continue
            s = raw_s.strip()
            if (
                len(s) > 25
                or s.startswith("#")
                or "```" in s
                or "missing row_number" in s.lower()
                or "http://" in s.lower()
                or "https://" in s.lower()
            ):
                suspicious_outside += 1
        if suspicious_outside >= 3:
            continue

        # Проверка порядка (хотя бы монотонного): id < source_type < ... < raw_title
        last = -1
        ordered = True
        for k in _RAW_FEED_HEADER_KEYS_DENSE_ORDER:
            if k not in positions_all:
                continue
            if positions_all[k] <= last:
                ordered = False
                break
            last = positions_all[k]
        if not ordered:
            continue

        matched_span_all = max(positions_all[k] for k in matched_all) - min(
            positions_all[k] for k in matched_all
        )
        if matched_span_all > 55:
            continue

        # Чем больше совпадений и чем плотнее — тем лучше.
        score = len(matched_all) * 1000 - span * 2 - matched_span_all

        trace = {
            "matched_columns": matched_all,
            "matched_indices": {k: positions_all[k] for k in matched_all},
            "dense_present": dense_present,
            "dense_span": span,
            "matched_span_all": matched_span_all,
            "reason": (
                "Строка принята как header row: "
                f"совпало колонок={len(matched_all)}, плотный span по dense={span}, "
                f"порядок dense-колонок соблюдён, подозрительных контентных ячеек не обнаружено."
            ),
            "score": score,
            "non_empty_cells": non_empty,
        }

        if best is None or score > best[1].get("score", -1):
            best = (idx, trace)

    if best is None:
        return None, {"reason": "candidates not found", "matched_columns": []}
    return best[0], best[1]


def _detect_parser_header_row(rows: list[list[str]]) -> int | None:
    idx, _trace = _detect_parser_header_row_with_trace(rows)
    return idx


def _get_cache_ttl() -> int:
    """Получает TTL кэша из конфига."""
    try:
        if current_app:
            return int(current_app.config.get("BLOG_SHEETS_CACHE_TTL", "120"))
    except Exception:
        pass
    return int(os.getenv("BLOG_SHEETS_CACHE_TTL", "120"))


def _extract_title_from_markdown(text: str) -> str:
    if not text:
        return ""
    match = re.search(r"^\s*#\s+(.+)$", text, flags=re.MULTILINE)
    if match:
        return match.group(1).strip()
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    return first_line[:120]


def _clean_title_noise(title: str) -> str:
    """
    Убирает служебный шум из конца заголовка:
    - хвосты вида #1234 / №1234
    - оставшиеся в конце одиночные эмодзи/символы после удаления номера
    """
    if not title:
        return ""

    s = str(title).strip()

    # Убираем хвост вида "#1234" или "№1234" только в конце строки
    s = re.sub(r"\s*[#№]\s*\d+\s*$", "", s).strip()

    # Убираем висящие в конце эмодзи/символьные токены без букв и цифр
    tokens = s.split()
    while tokens and not re.search(r"[A-Za-zА-Яа-яЁё0-9]", tokens[-1]):
        tokens.pop()

    s = " ".join(tokens).strip()
    s = re.sub(r"\s+", " ", s)

    return s


def _make_excerpt_from_content(text: str, limit: int = 220) -> str:
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", str(text))
    clean = re.sub(r"\s+", " ", clean).strip()
    if len(clean) <= limit:
        return clean
    return clean[:limit].rsplit(" ", 1)[0] + "…"


def _sanitize_preview_text(text: str) -> str:
    """
    Очистка текста для карточек блога: без markdown-заголовков, тестовых хвостов и служебных фраз.
    Не изменяет полный content_md поста — только цепочку для excerpt.
    """
    if not text:
        return ""
    raw = re.sub(r"<[^>]+>", " ", str(text))
    raw = raw.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not raw:
        return ""

    lines_out: List[str] = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        if "missing row_number" in line.lower():
            continue
        line = re.sub(r"^#{1,6}\s+", "", line)
        line = _RE_SITE_TEST_TOKEN.sub("", line)
        line = line.strip(" ,.;—-")
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines_out.append(line)

    joined = " ".join(lines_out)
    joined = _RE_SITE_TEST_TOKEN.sub("", joined)
    joined = re.sub(r"\s+", " ", joined).strip()
    return joined


def _excerpt_from_raw_string(s: str, limit: int = 220) -> str:
    """Санитизация + усечение; пустая строка, если нечего показать."""
    cleaned = _sanitize_preview_text(s)
    if not cleaned:
        return ""
    out = _make_excerpt_from_content(cleaned, limit=limit)
    return (out[:280] if out else "").strip()


def _card_excerpt_from_sources(*sources: Optional[str]) -> str:
    """
    Берёт первый источник (excerpt, summary, lead, тело …), даёт очищенный превью-текст
    или FALLBACK_BLOG_CARD_EXCERPT.
    """
    for v in sources:
        if v is None:
            continue
        chunk = str(v).strip()
        if not chunk:
            continue
        ex = _excerpt_from_raw_string(chunk)
        if ex:
            return ex
    return FALLBACK_BLOG_CARD_EXCERPT


def _extract_first_media(raw_media: str) -> str:
    if not raw_media:
        return ""
    text = str(raw_media).strip()
    if text.startswith("[") or text.startswith("{"):
        try:
            data = json.loads(text)
            if isinstance(data, list) and data:
                first = data[0]
                if isinstance(first, str):
                    return first
                if isinstance(first, dict):
                    return first.get("url") or first.get("path") or ""
            if isinstance(data, dict):
                return data.get("url") or data.get("path") or ""
        except Exception:
            return ""
    return text


_IMAGE_FIELD_KEYS = (
    "cover_image_url",
    "image_url",
    "thumbnail_url",
    "thumb_url",
    "poster_url",
    "poster",
    "image",
    "cover",
    "preview_image_url",
)


_LOCALHOST_STATIC_MEDIA_RE = re.compile(
    r"^https?://(?:127\.0\.0\.1|localhost)(?::\d+)?(/static/.+)$",
    re.IGNORECASE,
)


def _normalize_media_url(value: object) -> str:
    s = "" if value is None else str(value).strip()
    if not s:
        return ""
    if s.startswith("//"):
        return f"https:{s}"
    m = _LOCALHOST_STATIC_MEDIA_RE.match(s)
    if m:
        return m.group(1)
    return s


def _is_image_like_url(url: str) -> bool:
    s = _normalize_media_url(url)
    if not s:
        return False
    if s.startswith("/"):
        return True
    if s.startswith("data:image/") or s.startswith("blob:"):
        return True

    try:
        p = urlparse(s)
    except Exception:
        return False

    host = (p.netloc or "").lower()
    path = p.path or ""
    path_lower = path.lower()

    # Ссылки на Telegram-посты (t.me/channel/123) — это HTML-страницы, не image asset.
    if host in ("t.me", "telegram.me", "www.t.me", "www.telegram.me"):
        parts = [part for part in path.split("/") if part]
        if len(parts) == 2 and parts[1].isdigit():
            return False

    if re.search(r"\.(png|jpe?g|webp|gif|avif|bmp|svg)$", path_lower):
        return True

    # Для CDN/resize-ссылок без расширения допускаем известные media/path-маркеры.
    if any(token in path_lower for token in ("/file/", "/photo/", "/media/", "/images/", "/img/")):
        return True

    return False


def _extract_media_candidate(item: object) -> str:
    if isinstance(item, str):
        candidate = _normalize_media_url(item)
        return candidate if _is_image_like_url(candidate) else ""

    if isinstance(item, dict):
        for key in (
            "cover_image_url",
            "image_url",
            "thumbnail_url",
            "thumb_url",
            "poster_url",
            "poster",
            "secure_url",
            "url",
            "src",
            "path",
            "file_url",
        ):
            candidate = _normalize_media_url(item.get(key))
            if candidate and _is_image_like_url(candidate):
                return candidate

    return ""


def _parse_media_json_items(raw: object) -> List[object]:
    """Разбирает media_json / raw_media в список элементов."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        nested = raw.get("items") or raw.get("media") or raw.get("attachments")
        if isinstance(nested, list):
            return nested
        return [raw]

    text = str(raw).strip()
    if not text:
        return []
    if text.startswith("[") or text.startswith("{"):
        try:
            data = json.loads(text)
        except Exception:
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            nested = data.get("items") or data.get("media") or data.get("attachments")
            if isinstance(nested, list):
                return nested
            return [data]
        return []

    return [text]


def _embed_media_from_json(raw: object, exclude_url: str = "") -> str:
    """
    HTML дополнительных медиа для тела поста из media_json.
    exclude_url — обложка, чтобы не дублировать hero-картинку.
    """
    from markupsafe import escape

    exclude = _normalize_media_url(exclude_url)
    items = _parse_media_json_items(raw)
    if not items:
        return ""

    parts: List[str] = []
    seen: set[str] = set()
    if exclude:
        seen.add(exclude)

    for item in items:
        media_type = ""
        url = ""
        if isinstance(item, dict):
            media_type = str(item.get("type") or "").lower()
            url = _extract_media_candidate(item)
            if not url:
                url = _normalize_media_url(item.get("url") or item.get("src") or item.get("file_url") or "")
        else:
            url = _normalize_media_url(item)

        if not url or url in seen:
            continue
        if exclude and url == exclude:
            continue
        seen.add(url)

        is_video = media_type == "video" or (
            not _is_image_like_url(url)
            and bool(re.search(r"\.(mp4|webm|mov)(\?|$)", url, re.IGNORECASE))
        )
        if is_video:
            parts.append(
                '<figure class="blog-post-embedded-media">'
                f'<video controls playsinline preload="metadata" src="{escape(url)}"></video>'
                "</figure>"
            )
        elif _is_image_like_url(url):
            parts.append(
                '<figure class="blog-post-embedded-media">'
                f'<img src="{escape(url)}" alt="" loading="lazy" decoding="async">'
                "</figure>"
            )

    return "\n".join(parts)


def _extract_cover_image(row: Dict) -> str:
    # 1. Сначала ищем прямые поля строки
    for key in _IMAGE_FIELD_KEYS:
        candidate = _normalize_media_url(row.get(key))
        if candidate and _is_image_like_url(candidate):
            return candidate

    # 2. Затем пытаемся распарсить media-поля
    for raw_key in ("media_json", "raw_media", "media", "attachments"):
        raw_val = row.get(raw_key)
        if not raw_val:
            continue

        data = None

        if isinstance(raw_val, (list, dict)):
            data = raw_val
        else:
            text = str(raw_val).strip()
            if not text:
                continue

            if text.startswith("[") or text.startswith("{"):
                try:
                    data = json.loads(text)
                except Exception:
                    data = None
            else:
                data = text

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and str(item.get("type") or "").lower() == "image":
                    candidate = _extract_media_candidate(item)
                    if candidate:
                        return candidate

            for item in data:
                candidate = _extract_media_candidate(item)
                if candidate:
                    return candidate

        elif isinstance(data, dict):
            candidate = _extract_media_candidate(data)
            if candidate:
                return candidate

            nested = data.get("items") or data.get("media") or data.get("attachments")
            if isinstance(nested, list):
                for item in nested:
                    candidate = _extract_media_candidate(item)
                    if candidate:
                        return candidate

        elif isinstance(data, str):
            candidate = _normalize_media_url(data)
            if candidate and _is_image_like_url(candidate):
                return candidate

    return "/static/images/Place1Logo.png"


def _extract_video_urls_from_row(row: Dict) -> Tuple[str, str, str]:
    """
    (video_url, embed_url, video_poster_url) из raw_feed.
    См. docs/architecture/BLOG_RUNTIME_CANON.md — video_url, video_embed_url, video_preview_image_url.
    """
    video_url = _normalize_media_url(
        row.get("video_url")
        or row.get("video")
        or row.get("Video_URL")
        or ""
    )
    embed_url = _normalize_media_url(
        row.get("embed_url")
        or row.get("video_embed_url")
        or row.get("embed")
        or row.get("Video_Embed_Url")
        or ""
    )
    poster = ""
    for key in (
        "video_preview_image_url",
        "video_poster_url",
        "video_poster",
        "poster_url",
        "thumbnail_url",
        "thumb_url",
    ):
        c = _normalize_media_url(row.get(key))
        if c and _is_image_like_url(c):
            poster = c
            break
    return video_url, embed_url, poster


def _normalize_row_from_sheets(row: Dict) -> Optional[Dict]:
    """Нормализует строку из Sheets в формат поста."""
    if not is_publishable_row(row):
        return None
    
    sheet_id = str(row.get("id") or row.get("news_id") or row.get("raw_id") or "").strip()
    if not sheet_id:
        return None
    
    final_posts = str(row.get("final_posts") or "").strip()
    title = str(
        row.get("title")
        or row.get("raw_title")
        or _extract_title_from_markdown(final_posts)
        or ""
    ).strip()
    if not title:
        title = f"Материал {sheet_id}"

    title = _clean_title_noise(title)
    title_display = plain_title_for_display(title)
    title_display = _clean_title_noise(title_display)

    if not title_display:
        title_display = f"Материал {sheet_id}"

    # Контент
    content_md = str(
        row.get("final_posts")
        or row.get("text")
        or row.get("raw_content")
        or ""
    ).strip()
    content_html = safe_render_markdown(content_md) if content_md else str(row.get("raw_html") or "").strip()
    
    # Excerpt для карточек: только очищенный текст, без сырого markdown/тестовых хвостов
    excerpt = _card_excerpt_from_sources(
        row.get("excerpt"),
        row.get("summary"),
        row.get("lead"),
        content_md or str(row.get("raw_content") or "").strip() or None,
    )
    
    # Slug
    sheet_slug = str(row.get("slug") or "").strip()
    slug = sheet_slug if sheet_slug else _slugify(title_display, sheet_id)
    
    # Tags
    tags = _parse_tags(row.get("raw_tags") or row.get("tags"), row.get("ne"))
    
    # Published at
    published_at = _safe_dt(row.get("published_at")) or _safe_dt(row.get("updated_at")) or _safe_dt(row.get("created_at")) or datetime.utcnow()
    
    # Cover image
    cover = _extract_cover_image(row)
    video_url, embed_url, video_poster = _extract_video_urls_from_row(row)
    card_image = video_poster or cover

    if _blog_excerpt_trace_enabled():
        logger.info(
            "[blog-store] excerpt_trace slug=%s sheet_id=%s excerpt_len=%s",
            slug,
            sheet_id,
            len(excerpt or ""),
            extra={
                "event": "blog_excerpt_trace",
                "slug": slug,
                "sheet_id": sheet_id,
                "src_excerpt": _clip_for_log(row.get("excerpt")),
                "src_summary": _clip_for_log(row.get("summary")),
                "src_lead": _clip_for_log(row.get("lead")),
                "src_final_posts": _clip_for_log(final_posts, 400),
                "normalized_excerpt": _clip_for_log(excerpt, 320),
            },
        )

    result: Dict = {
        "id": sheet_id,
        "title": title_display,
        "slug": slug,
        "excerpt": excerpt,
        "content_md": content_md,
        "content_html": content_html,
        "cover_image_url": cover,
        "image_url": cover,
        "cover": cover,
        "poster_image_url": cover,
        "card_image_url": card_image,
        "video_url": video_url or None,
        "embed_url": embed_url or None,
        "video_poster_url": video_poster or None,
        "tags": tags,
        "tags_json": json.dumps(tags, ensure_ascii=False) if tags else None,
        "published_at": published_at,
        "updated_at": _safe_dt(row.get("updated_at")) or published_at,
        "source_type": str(row.get("source_type") or "").strip() or None,
        "source_name": str(row.get("source_name") or "").strip() or None,
        "source_url": str(row.get("source_url") or "").strip() or None,
        "status": str(row.get("status") or "").strip() or None,
        "author": str(row.get("author") or "").strip() or None,
    }
    attach_video_display_fields(result)
    return result


def _load_records_parser_aware() -> Tuple[List[Dict], List[str]]:
    """
    Parser-aware чтение raw_feed: ищем реальную строку заголовков и отбрасываем legacy-блок сверху.
    Если схема не распознана — fallback на fetch_parser_news_rows().
    """
    try:
        spreadsheet_id, worksheet_title = resolve_parser_source()
        svc = get_google_services()[1]
        result = svc.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"{worksheet_title}!A1:ZZ1000",
        ).execute()
        all_rows = result.get("values", [])
        if not all_rows:
            return [], []

        header_idx = None
        if worksheet_title == "raw_feed":
            header_idx = _detect_parser_header_row(all_rows)

        if header_idx is not None:
            headers = [str(x).strip() for x in all_rows[header_idx]]
            data_rows = all_rows[header_idx + 1 :]
        else:
            headers = [str(x).strip() for x in all_rows[0]]
            data_rows = all_rows[1:]

        records: List[Dict] = []
        for row in data_rows:
            if not any(str(cell).strip() for cell in row if cell is not None):
                continue
            padded = list(row) + [""] * max(0, len(headers) - len(row))
            records.append(dict(zip(headers, padded[: len(headers)])))
        return records, headers
    except Exception:
        return fetch_parser_news_rows()


def _load_from_sheets() -> List[Dict]:
    """Загружает посты из Sheets с кэшированием."""
    now = time.time()
    cached = _cache.get("sheets_data", {})
    cache_ttl = _get_cache_ttl()
    
    # Проверяем кэш
    if cached and now - cached.get("ts", 0) < cache_ttl:
        logger.debug("[blog-store] Используем кэшированные данные из Sheets")
        return cached.get("data", [])
    
    try:
        records, headers = _load_records_parser_aware()
        header_set = {str(h or "").strip().lower() for h in headers}
        parser_keys = {"id", "source_type", "raw_title", "final_posts", "summary", "status", "slug", "published_at"}
        parser_score = len(parser_keys.intersection(header_set))
        if parser_score < 5:
            logger.warning(
                "[blog-store] raw_feed header выглядит нестабильно для parser-схемы (score=%s). "
                "Используем текущий fallback-парсинг records.",
                parser_score,
            )
        posts = []
        seen_slugs = set()
        
        for row in records:
            normalized = _normalize_row_from_sheets(row)
            if not normalized:
                continue
            
            slug = normalized["slug"]
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)
            posts.append(normalized)
        
        # Сортируем по дате публикации
        posts.sort(key=lambda p: p.get("published_at") or datetime.utcnow(), reverse=True)
        
        # Обновляем кэш
        _cache["sheets_data"] = {"ts": now, "data": posts}
        logger.info(f"[blog-store] Загружено {len(posts)} постов из Sheets")
        return posts
        
    except Exception as e:
        logger.error(f"[blog-store] Ошибка чтения Sheets: {e}")
        # Возвращаем кэш если есть, даже если он устарел
        if cached.get("data"):
            logger.warning("[blog-store] Используем устаревший кэш из Sheets")
            return cached.get("data", [])
        return []


def _load_from_db() -> List[Dict]:
    """Загружает посты из БД (резерв)."""
    try:
        posts = BlogPost.query.filter(
            (BlogPost.status.in_(list(DB_PUBLISHABLE_STATUS_VALUES))) |
            (BlogPost.status.is_(None))
        ).filter(
            BlogPost.content_html.isnot(None) | BlogPost.content.isnot(None)
        ).order_by(BlogPost.published_at.desc().nullslast()).all()
        
        result = []
        for p in posts:
            if not is_publishable_blog_post_record(p):
                continue
            tags = []
            if p.tags_json:
                try:
                    tags = json.loads(p.tags_json)
                except Exception:
                    pass

            cover = p.cover_image_url or "/static/images/Place1Logo.png"

            rec: Dict = {
                "id": p.id,
                "title": _clean_title_noise(plain_title_for_display(p.title)),
                "slug": p.slug,
                "excerpt": _card_excerpt_from_sources(
                    p.excerpt,
                    p.teaser,
                    p.content_md,
                    p.content_html,
                    p.content,
                ),
                "content_md": p.content_md,
                "content_html": p.content_html or p.content,
                "cover_image_url": cover,
                "image_url": cover,
                "cover": cover,
                "poster_image_url": cover,
                "card_image_url": cover,
                "video_url": None,
                "embed_url": None,
                "video_poster_url": None,
                "tags": tags,
                "tags_json": p.tags_json,
                "published_at": p.published_at,
                "source_type": p.source_type,
                "source_name": p.source_name,
                "source_url": p.source_url,
                "status": p.status,
            }
            attach_video_display_fields(rec)
            result.append(rec)
        
        logger.info(f"[blog-store] Загружено {len(result)} постов из БД (резерв)")
        return result
        
    except Exception as e:
        logger.error(f"[blog-store] Ошибка чтения БД: {e}")
        return []


def get_posts(page: int = 1, limit: int = 10, prefer_sheets: bool = True) -> Tuple[List[Dict], int]:
    """
    Получает посты с пагинацией.
    prefer_sheets=True: сначала Sheets, fallback на БД
    prefer_sheets=False: только БД
    """
    if page < 1:
        page = 1
    if limit < 1:
        limit = 10
    
    posts = []
    
    if prefer_sheets:
        # Пытаемся загрузить из Sheets (источник истины)
        posts = _load_from_sheets()
        
        # Если Sheets пуст или ошибка - fallback на БД
        if not posts:
            logger.info("[blog-store] Sheets пуст/ошибка, используем БД как резерв")
            posts = _load_from_db()
    else:
        # Только БД
        posts = _load_from_db()
    
    total = len(posts)
    start = (page - 1) * limit
    end = start + limit
    return posts[start:end], total


def get_post_by_slug(slug: str, prefer_sheets: bool = True) -> Optional[Dict]:
    """Получает пост по slug."""
    if prefer_sheets:
        posts = _load_from_sheets()
        for p in posts:
            if p.get("slug") == slug:
                return p
        
        # Fallback на БД
        logger.debug(f"[blog-store] Пост {slug} не найден в Sheets, проверяем БД")
    
    # Ищем в БД
    try:
        post = BlogPost.query.filter_by(slug=slug).first()
        if post and is_publishable_blog_post_record(post):
            tags = []
            if post.tags_json:
                try:
                    tags = json.loads(post.tags_json)
                except Exception:
                    pass

            cover = post.cover_image_url or "/static/images/Place1Logo.png"

            out: Dict = {
                "id": post.id,
                "title": _clean_title_noise(plain_title_for_display(post.title)),
                "slug": post.slug,
                "excerpt": _card_excerpt_from_sources(
                    post.excerpt,
                    post.teaser,
                    post.content_md,
                    post.content_html,
                    post.content,
                ),
                "content_md": post.content_md,
                "content_html": post.content_html or post.content,
                "cover_image_url": cover,
                "image_url": cover,
                "cover": cover,
                "poster_image_url": cover,
                "card_image_url": cover,
                "video_url": None,
                "embed_url": None,
                "video_poster_url": None,
                "tags": tags,
                "tags_json": post.tags_json,
                "published_at": post.published_at,
                "source_type": post.source_type,
                "source_name": post.source_name,
                "source_url": post.source_url,
                "status": post.status,
            }
            attach_video_display_fields(out)
            return out
    except Exception as e:
        logger.error(f"[blog-store] Ошибка поиска в БД: {e}")
    
    return None


def get_latest_post(prefer_sheets: bool = True) -> Optional[Dict]:
    """Получает последний пост."""
    posts, _ = get_posts(page=1, limit=1, prefer_sheets=prefer_sheets)
    return posts[0] if posts else None
