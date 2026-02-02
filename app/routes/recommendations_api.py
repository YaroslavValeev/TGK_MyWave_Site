from flask import Blueprint, request, jsonify, current_app
from app.services.recommendations_service import (
    recommend,
    get_cache_stats,
    reset_cache_stats,
)

reco_bp = Blueprint("reco_bp", __name__)


@reco_bp.route("/reco", methods=["GET"])
def get_recommendations():
    """Простейший API для получения рекомендаций.

    Параметры:
      context: index|services|projects|blog_post|book_success
      user_key: (опционально) — значение для A/B сплита
      city, slug — дополнительные фильтры (необязательно)
    """
    context = request.args.get("context", "index")
    user_key = request.args.get("user_key") or request.cookies.get("session")
    city = request.args.get("city")
    slug = request.args.get("slug")
    limit = int(request.args.get("limit", 4))

    items = recommend(
        context=context, user_key=user_key, city=city, slug=slug, limit=limit
    )
    if not items:
        return ("", 204)
    return jsonify(items)


@reco_bp.route("/reco/stats", methods=["GET"])
def get_recommendations_stats():
    """Возвращает статистику работы кэша рекомендаций.

    Полезно для мониторинга эффективности кэширования.

    Response:
      {
        "hits": int,
        "misses": int,
        "hit_rate": float (0-100),
        "cache_size": int,
        "ttl_seconds": int,
        "total_requests": int
      }
    """
    stats = get_cache_stats()
    return jsonify(stats)


@reco_bp.route("/reco/stats/reset", methods=["POST"])
def reset_recommendations_stats():
    """Сбрасывает счётчики метрик кэша.

    Требует наличия ADMIN_TOKEN в заголовке X-Admin-Token
    или может быть ограничено по IP.
    """
    admin_token = current_app.config.get("ADMIN_TOKEN")
    if admin_token:
        provided_token = request.headers.get("X-Admin-Token", "")
        if provided_token != admin_token:
            return {"error": "Unauthorized"}, 401

    reset_cache_stats()
    return jsonify({"ok": True, "message": "Cache stats reset"})
