"""
Синхронизация блога из Google Sheets (PARSER_TAB) в локальную БД.
"""
import json
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from dateutil.parser import parse as dt_parse
    DATEUTIL_AVAILABLE = True
except ImportError:
    DATEUTIL_AVAILABLE = False

from app.services.parser_news_sheet import fetch_parser_news_rows
from app.services.blog.render import safe_render_markdown
from app.database.models import BlogPost, db

# --- helpers ---

PUBLISHABLE_STATUSES = {"READY_TO_PUBLISH", "PUBLISHED", "published"}


def _as_bool(v: Any) -> bool:
    """Конвертирует значение в bool."""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    s = str(v or "").strip().lower()
    return s in {"1", "true", "yes", "y", "да"}


def _safe_dt(v: Any) -> Optional[datetime]:
    """Безопасный парсинг даты."""
    if not v:
        return None
    if isinstance(v, datetime):
        return v
    if DATEUTIL_AVAILABLE:
        try:
            return dt_parse(str(v))
        except Exception:
            pass
    # Fallback: простые форматы
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(str(v), fmt)
        except Exception:
            continue
    return None


def _stable_checksum(row: Dict[str, Any]) -> str:
    """Вычисляет стабильный checksum для дедупликации."""
    # если checksum уже есть — используем его
    if row.get("checksum"):
        return str(row["checksum"]).strip()

    base = {
        "id": row.get("id"),
        "raw_title": row.get("raw_title"),
        "final_posts": row.get("final_posts"),
        "expert_opinion": row.get("expert_opinion"),
        "user_answers": row.get("user_answers"),
        "answer_text": row.get("answer_text"),
        "updated_at": row.get("updated_at"),
    }
    blob = json.dumps(base, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _slugify(title: str, post_id: str) -> str:
    """Генерирует безопасный slug."""
    t = (title or "").strip().lower()
    t = t.replace("ё", "е")
    t = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in t)
    t = "-".join([p for p in t.split("-") if p])
    if not t:
        t = "post"
    short = hashlib.md5((post_id or "").encode("utf-8")).hexdigest()[:6]
    return f"{t}-{short}"


def _parse_tags(raw_tags: Any, ne: Any) -> List[str]:
    """Парсит теги из разных источников."""
    tags: List[str] = []
    for src in [raw_tags, ne]:
        if not src:
            continue
        if isinstance(src, list):
            tags += [str(x).strip() for x in src if str(x).strip()]
        else:
            s = str(src).strip()
            # поддержка "tag1, tag2" и JSON
            if s.startswith("[") and s.endswith("]"):
                try:
                    arr = json.loads(s)
                    if isinstance(arr, list):
                        tags += [str(x).strip() for x in arr if str(x).strip()]
                        continue
                except Exception:
                    pass
            tags += [x.strip() for x in s.replace(";", ",").split(",") if x.strip()]
    # uniq preserve order
    out: List[str] = []
    seen = set()
    for t in tags:
        t2 = t.lower()
        if t2 not in seen:
            seen.add(t2)
            out.append(t)
    return out


def _is_publishable(row: Dict[str, Any]) -> bool:
    """Проверяет, можно ли публиковать строку."""
    status = str(row.get("status") or "").strip().upper()
    published_posts = _as_bool(row.get("published_posts"))
    final_posts = str(row.get("final_posts") or "").strip()
    
    # Если есть news_articles с готовыми полями
    if row.get("title") and row.get("text"):
        status_lower = status.lower()
        return status_lower in PUBLISHABLE_STATUSES or published_posts
    
    # Для raw_feed: нужен final_posts
    return bool(final_posts) and (status in PUBLISHABLE_STATUSES or published_posts)


def sync_blog_from_parser_tab(db_session, logger=None) -> Dict[str, int]:
    """
    Синхронизирует блог из PARSER_TAB в локальную БД.
    Возвращает статистику: created, updated, skipped, hidden
    """
    try:
        records, headers = fetch_parser_news_rows()
    except Exception as e:
        if logger:
            logger.error(f"[blog-sync] Ошибка чтения Sheets: {e}")
        return {"created": 0, "updated": 0, "skipped": 0, "hidden": 0, "error": str(e)}

    created = 0
    updated = 0
    skipped = 0
    hidden = 0  # непубликуемые

    for row in records:
        sheet_id = str(row.get("id") or row.get("news_id") or row.get("raw_id") or "").strip()
        if not sheet_id:
            skipped += 1
            continue

        publishable = _is_publishable(row)
        if not publishable:
            hidden += 1
            continue

        title = str(row.get("title") or row.get("raw_title") or "").strip()
        if not title:
            title = f"Материал {sheet_id}"

        checksum = _stable_checksum(row)

        post = db_session.get(BlogPost, sheet_id)
        if post and post.checksum == checksum:
            skipped += 1
            continue

        # контент
        final_posts = str(row.get("final_posts") or row.get("text") or "").strip()
        content_md = final_posts
        content_html = safe_render_markdown(content_md)

        # excerpt
        summary = str(row.get("summary") or row.get("lead") or "").strip()
        excerpt = summary[:280] if summary else None

        tags = _parse_tags(row.get("raw_tags") or row.get("tags"), row.get("ne"))

        # published_at
        published_at = _safe_dt(row.get("published_at")) or _safe_dt(row.get("updated_at")) or _safe_dt(row.get("created_at")) or datetime.utcnow()

        if not post:
            post = BlogPost(
                id=sheet_id,
                title=title,
                slug=_slugify(title, sheet_id),
            )
            created += 1
        else:
            updated += 1

        post.source_type = str(row.get("source_type") or "").strip() or None
        post.source_name = str(row.get("source_name") or "").strip() or None
        post.source_url = str(row.get("source_url") or "").strip() or None

        post.title = title
        # slug: если в Sheets есть поле slug — уважаем его
        sheet_slug = str(row.get("slug") or "").strip()
        if sheet_slug:
            post.slug = sheet_slug
        elif not post.slug:
            post.slug = _slugify(title, sheet_id)

        post.excerpt = excerpt
        post.content_md = content_md
        post.content_html = content_html
        # Обратная совместимость
        post.content = content_html
        post.teaser = excerpt

        # cover
        cover = str(row.get("cover_image_url") or row.get("image_url") or "").strip()
        if not cover:
            # пробуем raw_media
            raw_media = row.get("raw_media")
            if raw_media:
                s = str(raw_media).strip()
                if s.startswith("[") and s.endswith("]"):
                    try:
                        arr = json.loads(s)
                        if isinstance(arr, list) and arr:
                            cover = str(arr[0])
                    except Exception:
                        pass
                elif s.startswith("http"):
                    cover = s
        post.cover_image_url = cover or None

        post.tags_json = json.dumps(tags, ensure_ascii=False) if tags else None
        post.lang = str(row.get("lang") or "").strip() or None
        post.checksum = checksum
        post.status = str(row.get("status") or "").strip() or None

        try:
            post.sheet_row_number = int(row.get("row_number") or 0) or None
        except Exception:
            post.sheet_row_number = None

        post.published_at = published_at

        db_session.add(post)

    try:
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        if logger:
            logger.error(f"[blog-sync] Ошибка коммита: {e}")
        return {"created": 0, "updated": 0, "skipped": 0, "hidden": 0, "error": str(e)}

    if logger:
        logger.info(f"[blog-sync] created={created}, updated={updated}, skipped={skipped}, hidden={hidden}")

    return {"created": created, "updated": updated, "skipped": skipped, "hidden": hidden}
