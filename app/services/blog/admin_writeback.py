"""
Admin writeback в raw_feed: site/SEO/карточка + тело/видео (B4.2).

Не пишет: raw_content, ingest/process/parse, approval.
final_posts / video_* — явное site editorial override в Sheets (осторожно с Parser).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from app.modules.logger import get_logger
from app.services.blog.display_text import plain_excerpt_for_display, plain_title_for_display
from app.services.blog.publish import (
    _column_index_to_letter,
    _find_column_index,
    update_sheet_cells,
)
from app.services.blog.store import invalidate_blog_sheets_cache
from app.services.blog.sync import _slugify
from app.services.parser_news_sheet import resolve_parser_source
from app.services.google import read_sheet

logger = get_logger(__name__)

# B4.2: витрина/SEO + тело статьи + video URLs.
ADMIN_WRITABLE_COLUMNS = (
    "excerpt",
    "summary",
    "cover_image_url",
    "raw_tags",
    "seo_title",
    "meta_description",
    "og_title",
    "og_description",
    "slug",
    "final_posts",
    "video_url",
    "embed_url",
    "video_embed_url",
    "video_preview_image_url",
)

ADMIN_STATUS_VALUES = frozenset({"PUBLISHED", "READY_TO_PUBLISH", "ARCHIVED"})

# Google Sheets cell soft limit ~50k; оставляем запас.
_MAX_FINAL_POSTS_CHARS = 48000


def _norm_tags(raw: str) -> str:
    parts = [p.strip() for p in re.split(r"[,;]", raw or "") if p.strip()]
    out: List[str] = []
    seen = set()
    for p in parts:
        key = p.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return ", ".join(out[:12])


def _safe_slug(value: str, fallback_id: str) -> str:
    s = (value or "").strip().lower()
    if not s:
        return ""
    if not s.isascii():
        return _slugify(s, fallback_id)
    cleaned = "".join(ch if (ch.isalnum() or ch in "-_") else "-" for ch in s)
    cleaned = "-".join(p for p in cleaned.split("-") if p)
    return cleaned[:80]


def _safe_https_url(value: str) -> str:
    s = (value or "").strip()
    if not s:
        return ""
    if s.startswith("//"):
        s = "https:" + s
    if s.startswith("/"):
        return s  # relative site path ok for cover/poster
    try:
        p = urlparse(s)
    except Exception:
        return ""
    if p.scheme.lower() not in ("http", "https"):
        return ""
    return s


def write_admin_fields(
    *,
    sheet_id: str,
    row_number: int,
    fields: Dict[str, Any],
    status: Optional[str] = None,
) -> Tuple[bool, str, List[str]]:
    """
    Пишет поля в строку raw_feed по row_number + сверке id.

    Returns: (ok, message, written_columns)
    """
    if row_number < 2:
        return False, "invalid_row_number", []
    if not sheet_id:
        return False, "missing_sheet_id", []

    try:
        spreadsheet_id, sheet_name = resolve_parser_source()
        records, headers = read_sheet(spreadsheet_id, sheet_name)
    except Exception as exc:
        logger.warning("admin_writeback_read_failed err=%s", type(exc).__name__)
        return False, "sheets_read_failed", []

    id_col = _find_column_index(headers, "id")
    if id_col is None:
        return False, "id_column_missing", []

    id_col_name = headers[id_col] if id_col is not None else "id"
    target = None
    for rec in records or []:
        rid = str(rec.get("id") or rec.get(id_col_name) or "").strip()
        if rid != str(sheet_id).strip():
            continue
        try:
            rn = int(str(rec.get("row_number") or "").strip() or "0")
        except Exception:
            rn = 0
        if rn >= 2:
            row_number = rn
        target = rec
        break

    if target is None:
        return False, "row_not_found", []

    updates: List[Dict[str, Any]] = []
    written: List[str] = []

    payload: Dict[str, str] = {}
    if "excerpt" in fields and fields.get("excerpt") is not None:
        excerpt = plain_excerpt_for_display(str(fields.get("excerpt") or ""), limit=400)
        payload["excerpt"] = excerpt
        payload["summary"] = excerpt
    if "cover_image_url" in fields and fields.get("cover_image_url") is not None:
        payload["cover_image_url"] = _safe_https_url(str(fields.get("cover_image_url") or ""))
    if "raw_tags" in fields and fields.get("raw_tags") is not None:
        payload["raw_tags"] = _norm_tags(str(fields.get("raw_tags") or ""))
    if "seo_title" in fields and fields.get("seo_title") is not None:
        payload["seo_title"] = plain_title_for_display(str(fields.get("seo_title") or ""), max_len=120)
    if "meta_description" in fields and fields.get("meta_description") is not None:
        payload["meta_description"] = plain_excerpt_for_display(
            str(fields.get("meta_description") or ""), limit=300
        )
    if "og_title" in fields and fields.get("og_title") is not None:
        payload["og_title"] = plain_title_for_display(str(fields.get("og_title") or ""), max_len=120)
    if "og_description" in fields and fields.get("og_description") is not None:
        payload["og_description"] = plain_excerpt_for_display(
            str(fields.get("og_description") or ""), limit=300
        )
    if "slug" in fields and fields.get("slug") is not None:
        new_slug = _safe_slug(str(fields.get("slug") or ""), sheet_id)
        if new_slug:
            payload["slug"] = new_slug

    # B4.2 body / media
    if "final_posts" in fields and fields.get("final_posts") is not None:
        body = str(fields.get("final_posts") or "")
        if len(body) > _MAX_FINAL_POSTS_CHARS:
            body = body[:_MAX_FINAL_POSTS_CHARS]
        payload["final_posts"] = body
    if "video_url" in fields and fields.get("video_url") is not None:
        payload["video_url"] = _safe_https_url(str(fields.get("video_url") or ""))
    if "embed_url" in fields and fields.get("embed_url") is not None:
        emb = _safe_https_url(str(fields.get("embed_url") or ""))
        payload["embed_url"] = emb
        # дублируем в video_embed_url, если колонка есть
        payload["video_embed_url"] = emb
    if "video_preview_image_url" in fields and fields.get("video_preview_image_url") is not None:
        payload["video_preview_image_url"] = _safe_https_url(
            str(fields.get("video_preview_image_url") or "")
        )

    for col_name, value in payload.items():
        if col_name not in ADMIN_WRITABLE_COLUMNS:
            continue
        idx = _find_column_index(headers, col_name)
        if idx is None:
            continue
        letter = _column_index_to_letter(idx)
        updates.append({"range": f"{letter}{row_number}", "values": [[value]]})
        written.append(col_name)

    if status:
        st = str(status).strip().upper()
        if st in ADMIN_STATUS_VALUES:
            idx = _find_column_index(headers, "status")
            if idx is not None:
                letter = _column_index_to_letter(idx)
                updates.append({"range": f"{letter}{row_number}", "values": [[st]]})
                written.append("status")

    if not updates:
        return False, "no_writable_columns_or_empty", []

    ok = update_sheet_cells(spreadsheet_id, sheet_name, updates)
    if not ok:
        return False, "sheets_write_failed", written

    invalidate_blog_sheets_cache()
    logger.info(
        "admin_writeback_ok",
        extra={"sheet_id": sheet_id, "row_number": row_number, "cols": ",".join(written)},
    )
    return True, "ok", written
