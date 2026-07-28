from flask import Blueprint, abort, current_app, jsonify, render_template, request

from app.extensions import csrf
from app.modules.logger import get_logger
from app.services.blog.display_text import plain_excerpt_for_display, plain_title_for_display
from app.services.blog.store import (
    get_posts,
    get_post_by_slug,
    get_latest_post,
    invalidate_blog_sheets_cache,
    _load_from_sheets,
    _load_from_db,
)

logger = get_logger(__name__)

blog_bp = Blueprint("blog", __name__, template_folder="../templates")


def _normalize_posts_for_template(posts: list) -> list:
    """Санитизация title/excerpt до рендера — не зависит от Jinja filter registry."""
    for p in posts:
        if not isinstance(p, dict):
            continue
        p["title"] = plain_title_for_display(p.get("title"))
        p["excerpt"] = plain_excerpt_for_display(p.get("excerpt"))
    return posts


def _blog_cache_invalidate_token_ok() -> bool:
    """Тот же секрет, что и для media upload — без отдельного ключа."""
    auth = (request.headers.get("Authorization") or "").strip()
    token = ""
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
    if not token:
        token = (request.headers.get("X-Media-Upload-Token") or "").strip()
    expected = (current_app.config.get("MEDIA_UPLOAD_TOKEN") or "").strip()
    if not expected:
        return False
    return token == expected


def _api_item_payload(p: dict) -> dict:
    cover = p.get("cover_image_url")
    card = p.get("card_image_url") or cover
    return {
        "title": p["title"],
        "lead": p.get("excerpt"),
        "slug": p["slug"],
        "published_at": p["published_at"].isoformat() if p.get("published_at") else None,
        "tags": p.get("tags", []),
        "cover_image_url": cover,
        "image_url": p.get("image_url") or cover,
        "cover": p.get("cover") or cover,
        "card_image_url": card,
        "video_url": p.get("video_url"),
        "embed_url": p.get("embed_url"),
        "video_poster_url": p.get("video_poster_url"),
    }


@blog_bp.get("/blog")
def blog_index():
    """
    Список постов: Sheets как источник истины, БД как резерв.
    """
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 12))
    tag = (request.args.get("tag") or "").strip().lower()
    query = (request.args.get("q") or "").strip()
    # Можно добавить ?db_only=1 для принудительного использования БД
    prefer_sheets = request.args.get("db_only") != "1"

    try:
        # Получаем расширенный набор, чтобы корректно фильтровать перед пагинацией.
        items, _ = get_posts(page=1, limit=1000, prefer_sheets=prefer_sheets)
    except Exception as e:
        logger.error(f"blog: ошибка загрузки постов: {e}")
        items = []

    # Фильтр по тегу (если задан)
    if tag and items:
        items = [p for p in items if tag.lower() in [t.lower() for t in (p.get("tags") or [])]]

    # Поиск по заголовку, excerpt и контенту.
    if query and items:
        q = query.lower()
        items = [
            p for p in items
            if q in str(p.get("title") or "").lower()
            or q in str(p.get("excerpt") or "").lower()
            or q in str(p.get("content_md") or "").lower()
            or q in str(p.get("content_html") or "").lower()
        ]

    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page
    items = items[start:end]
    items = _normalize_posts_for_template(items)

    # Простая пагинация
    has_next = (page * per_page) < total
    has_prev = page > 1

    try:
        return render_template(
            "blog/index.html",
            posts=items,
            page=page,
            per_page=per_page,
            total=total,
            has_next=has_next,
            has_prev=has_prev,
            tag=tag,
            q=query,
            meta_description=(
                "Новости, события и статьи MyWave: "
                "вейксёрфинг, тренировки, проекты и индустрия."
            ),
        )
    except Exception as render_err:
        logger.error("blog: ошибка рендера index: %s", render_err)
        return render_template(
            "blog/index.html",
            posts=[],
            page=1,
            per_page=per_page,
            total=0,
            has_next=False,
            has_prev=False,
            tag=tag,
            q=query,
            meta_description=(
                "Новости, события и статьи MyWave: "
                "вейксёрфинг, тренировки, проекты и индустрия."
            ),
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
    excerpt = (post.get("excerpt") or post.get("title") or "").strip()
    return render_template(
        "blog/post.html",
        post=post,
        tags=tags,
        meta_description=excerpt[:300] if excerpt else None,
    )


@blog_bp.get("/api/blog/latest")
def api_blog_latest():
    """API: последний пост (Sheets → БД fallback)."""
    prefer_sheets = request.args.get("db_only") != "1"
    
    try:
        post = get_latest_post(prefer_sheets=prefer_sheets)
        if not post:
            return jsonify({"error": "no posts"}), 404

        # Те же правила, что в items[] у /api/blog/posts
        return jsonify(_api_item_payload(post))
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
            "items": [_api_item_payload(p) for p in items],
        })
    except Exception as e:
        logger.error("blog: ошибка api posts: %s", e)
        return jsonify({"error": "unavailable"}), 503


@blog_bp.get("/api/blog/diagnostics")
def api_blog_diagnostics():
    """
    Read-only: откуда читается блог и сколько постов в Sheets vs SQLite.
    Не раскрывает полные ID таблиц и содержимое постов.
    """
    resolve_error = None
    parser_spreadsheet_tail = None
    parser_worksheet = None
    try:
        from app.services.parser_news_sheet import resolve_parser_source

        sid, wst = resolve_parser_source()
        parser_spreadsheet_tail = (sid or "")[-8:] if sid else None
        parser_worksheet = wst
    except Exception as e:
        resolve_error = str(e)

    try:
        sheets_posts = _load_from_sheets()
    except Exception as e:
        sheets_posts = []
        logger.warning("blog diagnostics: sheets load failed: %s", e)

    try:
        db_posts = _load_from_db()
    except Exception as e:
        db_posts = []
        logger.warning("blog diagnostics: db load failed: %s", e)

    vitrine_posts, _ = get_posts(page=1, limit=1000, prefer_sheets=True)

    return jsonify(
        {
            "parser_source": {
                "spreadsheet_id_tail": parser_spreadsheet_tail,
                "worksheet": parser_worksheet,
                "resolve_error": resolve_error,
            },
            "counts": {
                "sheets_publishable": len(sheets_posts),
                "db_publishable": len(db_posts),
                "vitrine_total": len(vitrine_posts) if vitrine_posts else 0,
            },
            "hint": (
                "Блог: PARSER_NEWS_SPREADSHEET_ID + PARSER_SHEET_NAME=raw_feed "
                "(Parser News), не SPREADSHEET_ID Admin/Tg Bot. "
                "Статус: READY_TO_PUBLISH или PUBLISHED + контент."
            ),
        }
    )


@blog_bp.post("/api/blog/cache/invalidate")
@csrf.exempt
def api_blog_cache_invalidate():
    """Сброс in-memory кэша Sheets (следующий запрос перечитает raw_feed)."""
    if not _blog_cache_invalidate_token_ok():
        return jsonify({"error": "forbidden"}), 403
    invalidate_blog_sheets_cache()
    return jsonify({"ok": True, "message": "blog sheets cache invalidated"})
