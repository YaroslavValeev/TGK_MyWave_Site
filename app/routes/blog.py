import json
from flask import Blueprint, abort, jsonify, render_template, request

from app.modules.logger import get_logger
from app.services.blog.store import get_posts, get_post_by_slug, get_latest_post

logger = get_logger(__name__)

blog_bp = Blueprint("blog", __name__, template_folder="../templates")


@blog_bp.get("/blog")
def blog_index():
    """
    Список постов: Sheets как источник истины, БД как резерв.
    """
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 12))
    tag = (request.args.get("tag") or "").strip().lower()
    # Можно добавить ?db_only=1 для принудительного использования БД
    prefer_sheets = request.args.get("db_only") != "1"

    try:
        items, total = get_posts(page=page, limit=per_page, prefer_sheets=prefer_sheets)
    except Exception as e:
        logger.error(f"blog: ошибка загрузки постов: {e}")
        items, total = [], 0

    # Фильтр по тегу (если задан)
    if tag and items:
        items = [p for p in items if tag.lower() in [t.lower() for t in (p.get("tags") or [])]]
        total = len(items)

    # Простая пагинация
    has_next = (page * per_page) < total
    has_prev = page > 1

    return render_template(
        "blog/index.html",
        posts=items,
        page=page,
        per_page=per_page,
        total=total,
        has_next=has_next,
        has_prev=has_prev,
        tag=tag,
    )


@blog_bp.get("/blog/<slug>")
def blog_post(slug: str):
    """
    Страница поста: Sheets как источник истины, БД как резерв.
    """
    prefer_sheets = request.args.get("db_only") != "1"
    post = get_post_by_slug(slug, prefer_sheets=prefer_sheets)
    
    if not post:
        abort(404)

    tags = post.get("tags", [])
    return render_template("blog/post.html", post=post, tags=tags)


@blog_bp.get("/api/blog/latest")
def api_blog_latest():
    """API: последний пост (Sheets → БД fallback)."""
    prefer_sheets = request.args.get("db_only") != "1"
    
    try:
        post = get_latest_post(prefer_sheets=prefer_sheets)
        if not post:
            return jsonify({"error": "no posts"}), 404
        
        return jsonify({
            "title": post["title"],
            "lead": post.get("excerpt"),
            "slug": post["slug"],
            "published_at": post["published_at"].isoformat() if post.get("published_at") else None,
            "tags": post.get("tags", []),
        })
    except Exception as e:
        logger.error("blog: ошибка api latest: %s", e)
        return jsonify({"error": "unavailable"}), 503


@blog_bp.get("/api/blog/posts")
def api_blog_posts():
    """API: список постов (Sheets → БД fallback)."""
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 10))
    prefer_sheets = request.args.get("db_only") != "1"
    
    try:
        items, total = get_posts(page=page, limit=limit, prefer_sheets=prefer_sheets)
        
        return jsonify({
            "page": page,
            "limit": limit,
            "total": total,
            "items": [
                {
                    "title": p["title"],
                    "lead": p.get("excerpt"),
                    "slug": p["slug"],
                    "published_at": p["published_at"].isoformat() if p.get("published_at") else None,
                    "tags": p.get("tags", []),
                    "image_url": p.get("cover_image_url"),
                }
                for p in items
            ],
        })
    except Exception as e:
        logger.error("blog: ошибка api posts: %s", e)
        return jsonify({"error": "unavailable"}), 503
