"""
Гибридный store для блога: Sheets как источник истины, БД как резерв/кэш.
"""
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from flask import current_app

from app.database.models import BlogPost, db
from app.modules.logger import get_logger
from app.services.parser_news_sheet import fetch_parser_news_rows
from app.services.blog.render import safe_render_markdown
from app.services.blog.sync import (
    _as_bool,
    _safe_dt,
    _slugify,
    _parse_tags,
    _is_publishable,
    PUBLISHABLE_STATUSES,
)

logger = get_logger(__name__)

# Кэш для Sheets данных (TTL 60-180 сек)
_cache: Dict[str, Dict] = {"sheets_data": {"ts": 0, "data": []}}


def _get_cache_ttl() -> int:
    """Получает TTL кэша из конфига."""
    try:
        if current_app:
            return int(current_app.config.get("BLOG_SHEETS_CACHE_TTL", "120"))
    except Exception:
        pass
    import os
    return int(os.getenv("BLOG_SHEETS_CACHE_TTL", "120"))


def _normalize_row_from_sheets(row: Dict) -> Optional[Dict]:
    """Нормализует строку из Sheets в формат поста."""
    if not _is_publishable(row):
        return None
    
    sheet_id = str(row.get("id") or row.get("news_id") or row.get("raw_id") or "").strip()
    if not sheet_id:
        return None
    
    title = str(row.get("title") or row.get("raw_title") or "").strip()
    if not title:
        title = f"Материал {sheet_id}"
    
    # Контент
    final_posts = str(row.get("final_posts") or row.get("text") or "").strip()
    content_md = final_posts
    content_html = safe_render_markdown(content_md)
    
    # Excerpt
    summary = str(row.get("summary") or row.get("lead") or "").strip()
    excerpt = summary[:280] if summary else None
    
    # Slug
    sheet_slug = str(row.get("slug") or "").strip()
    slug = sheet_slug if sheet_slug else _slugify(title, sheet_id)
    
    # Tags
    tags = _parse_tags(row.get("raw_tags") or row.get("tags"), row.get("ne"))
    
    # Published at
    published_at = _safe_dt(row.get("published_at")) or _safe_dt(row.get("updated_at")) or _safe_dt(row.get("created_at")) or datetime.utcnow()
    
    # Cover image
    cover = str(row.get("cover_image_url") or row.get("image_url") or "").strip()
    if not cover:
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
    
    return {
        "id": sheet_id,
        "title": title,
        "slug": slug,
        "excerpt": excerpt,
        "content_md": content_md,
        "content_html": content_html,
        "cover_image_url": cover or None,
        "tags": tags,
        "tags_json": json.dumps(tags, ensure_ascii=False) if tags else None,
        "published_at": published_at,
        "source_type": str(row.get("source_type") or "").strip() or None,
        "source_name": str(row.get("source_name") or "").strip() or None,
        "source_url": str(row.get("source_url") or "").strip() or None,
        "status": str(row.get("status") or "").strip() or None,
    }


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
        records, headers = fetch_parser_news_rows()
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
            (BlogPost.status.in_(["READY_TO_PUBLISH", "PUBLISHED", "published"])) |
            (BlogPost.status.is_(None))
        ).filter(
            BlogPost.content_html.isnot(None) | BlogPost.content.isnot(None)
        ).order_by(BlogPost.published_at.desc().nullslast()).all()
        
        result = []
        for p in posts:
            tags = []
            if p.tags_json:
                try:
                    tags = json.loads(p.tags_json)
                except Exception:
                    pass
            
            result.append({
                "id": p.id,
                "title": p.title,
                "slug": p.slug,
                "excerpt": p.excerpt,
                "content_md": p.content_md,
                "content_html": p.content_html or p.content,
                "cover_image_url": p.cover_image_url,
                "tags": tags,
                "tags_json": p.tags_json,
                "published_at": p.published_at,
                "source_type": p.source_type,
                "source_name": p.source_name,
                "source_url": p.source_url,
                "status": p.status,
            })
        
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
        if post:
            tags = []
            if post.tags_json:
                try:
                    tags = json.loads(post.tags_json)
                except Exception:
                    pass
            
            return {
                "id": post.id,
                "title": post.title,
                "slug": post.slug,
                "excerpt": post.excerpt,
                "content_md": post.content_md,
                "content_html": post.content_html or post.content,
                "cover_image_url": post.cover_image_url,
                "tags": tags,
                "tags_json": post.tags_json,
                "published_at": post.published_at,
                "source_type": post.source_type,
                "source_name": post.source_name,
                "source_url": post.source_url,
                "status": post.status,
            }
    except Exception as e:
        logger.error(f"[blog-store] Ошибка поиска в БД: {e}")
    
    return None


def get_latest_post(prefer_sheets: bool = True) -> Optional[Dict]:
    """Получает последний пост."""
    posts, _ = get_posts(page=1, limit=1, prefer_sheets=prefer_sheets)
    return posts[0] if posts else None
