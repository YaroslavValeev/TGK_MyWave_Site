"""Read-only Events API (Events-2)."""

from __future__ import annotations

from functools import wraps

from flask import Blueprint, jsonify, request

from app.config.events_features import (
    get_events_feature_flags,
    is_events_api_enabled,
    is_events_review_api_enabled,
)
from app.modules.logger import get_logger
from app.services.events.serializer import serialize_api_item
from app.services.events.store import get_diagnostics, list_items, list_review_queue

logger = get_logger(__name__)

events_api_bp = Blueprint("events_api", __name__)


def _api_disabled_response():
    return jsonify({"error": "events_api_disabled", "message": "Events API is not enabled"}), 503


def _require_events_api(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_events_api_enabled():
            return _api_disabled_response()
        return view(*args, **kwargs)

    return wrapped


def _require_review_api(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_events_review_api_enabled():
            return _api_disabled_response()
        return view(*args, **kwargs)

    return wrapped


def _items_response(result: dict) -> dict:
    return {
        "items": [serialize_api_item(it) for it in result["items"]],
        "count": result["count"],
        "total": result.get("total", result["count"]),
        "filters_applied": result.get("filters_applied", {}),
        "flags": get_events_feature_flags(),
    }


@events_api_bp.get("/api/events")
@_require_events_api
def api_events_list():
    result = list_items(
        content_type=request.args.get("content_type"),
        track_status=request.args.get("track_status"),
        city=request.args.get("city"),
        from_date=request.args.get("from_date"),
        to_date=request.args.get("to_date"),
        limit=request.args.get("limit", 50, type=int),
        offset=request.args.get("offset", 0, type=int),
        source=request.args.get("source", "all"),
    )
    return jsonify(_items_response(result))


@events_api_bp.get("/api/events/review-queue")
@_require_review_api
def api_events_review_queue():
    result = list_review_queue(
        limit=request.args.get("limit", 50, type=int),
        offset=request.args.get("offset", 0, type=int),
        source=request.args.get("source", "all"),
    )
    return jsonify(_items_response(result))


@events_api_bp.get("/api/events/diagnostics")
@_require_events_api
def api_events_diagnostics():
    diag = get_diagnostics(source=request.args.get("source", "all"))
    diag["flags"] = get_events_feature_flags()
    return jsonify(diag)
