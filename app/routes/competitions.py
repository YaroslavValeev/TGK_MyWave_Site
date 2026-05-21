from flask import Blueprint, current_app, jsonify, request

from app.extensions import csrf
from app.modules.logger import get_logger
from app.services.competitions.sheet import resolve_competitions_source
from app.services.competitions.store import (
    get_ticker_items,
    invalidate_competitions_sheets_cache,
)

logger = get_logger(__name__)

competitions_bp = Blueprint("competitions", __name__)


def _accepted_invalidate_tokens() -> set:
    """Токены для POST /api/competitions/cache/invalidate (без пустых)."""
    keys = ("MEDIA_UPLOAD_TOKEN", "COMPETITIONS_CACHE_INVALIDATE_TOKEN")
    out = set()
    for key in keys:
        val = (current_app.config.get(key) or "").strip()
        if val:
            out.add(val)
    return out


def _cache_invalidate_token_ok() -> bool:
    auth = (request.headers.get("Authorization") or "").strip()
    token = ""
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
    if not token:
        token = (request.headers.get("X-Media-Upload-Token") or "").strip()
    accepted = _accepted_invalidate_tokens()
    if not accepted:
        return False
    return token in accepted


def _api_item_payload(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "label": item.get("label"),
        "href": item.get("href"),
        "discipline": item.get("discipline"),
        "event_name": item.get("event_name"),
        "start_date": item.get("start_date"),
        "end_date": item.get("end_date"),
        "source_name": item.get("source_name"),
    }


@competitions_bp.get("/api/competitions/ticker")
def api_competitions_ticker():
    resolve_error = None
    spreadsheet_tail = None
    sheet_name = None
    try:
        sid, wst = resolve_competitions_source()
        spreadsheet_tail = (sid or "")[-8:] if sid else None
        sheet_name = wst
    except Exception as e:
        resolve_error = str(e)

    try:
        items = get_ticker_items()
    except Exception as e:
        logger.error("competitions_ticker_api_error: %s", e)
        return jsonify({"error": "unavailable"}), 503

    return jsonify(
        {
            "items": [_api_item_payload(it) for it in items],
            "count": len(items),
            "spreadsheet_id_tail": spreadsheet_tail,
            "sheet_name": sheet_name,
            "resolve_error": resolve_error,
            "hint": (
                "Ticker: PARSER_NEWS_SPREADSHEET_ID + COMPETITIONS_SHEET_NAME. "
                "status=ACTIVE, end_date >= today."
            ),
        }
    )


@competitions_bp.post("/api/competitions/cache/invalidate")
@csrf.exempt
def api_competitions_cache_invalidate():
    if not _cache_invalidate_token_ok():
        return jsonify({"error": "forbidden"}), 403
    invalidate_competitions_sheets_cache()
    return jsonify({"ok": True, "message": "competitions sheets cache invalidated"})
