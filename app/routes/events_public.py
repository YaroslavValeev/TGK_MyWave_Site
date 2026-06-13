"""Events-3 public vitrine routes."""

from __future__ import annotations

from flask import Blueprint, abort, redirect, render_template, request, url_for

from app.config.events_features import (
    is_events_api_enabled,
    is_events_public_ui_enabled,
    is_events_public_ui_flag_set,
)
from app.services.events.public_serializer import (
    build_public_json_ld_list,
    serialize_public_card,
    serialize_public_detail,
)
from app.services.events.public_urls import canonical_events_list_url, get_public_site_base_url
from app.services.events.store import get_public_items, resolve_public_item_by_slug
from app.services.showcases import get_event_cards, get_events_schema

events_public_bp = Blueprint("events_public", __name__)

_COMPETITIONS_REDIRECT_CODE = 302


def _yaml_events_context():
    return {
        "events_dynamic": False,
        "events": get_events_schema(),
        "event_cards": get_event_cards(),
        "canonical_url": None,
        "yaml_fallback": False,
        "empty_filter": False,
        "filter_type": None,
        "filter_city": None,
    }


def render_events_list():
    if not is_events_public_ui_flag_set():
        ctx = _yaml_events_context()
        return render_template("events.html", **ctx)

    if not is_events_api_enabled():
        ctx = _yaml_events_context()
        ctx["yaml_fallback"] = True
        ctx["api_unavailable"] = True
        return render_template("events.html", **ctx)

    content_type = (request.args.get("type") or request.args.get("content_type") or "").strip()
    city = (request.args.get("city") or "").strip()
    from_date = (request.args.get("from") or request.args.get("from_date") or "").strip() or None
    to_date = (request.args.get("to") or request.args.get("to_date") or "").strip() or None

    try:
        items = get_public_items(
            content_type=content_type or None,
            city=city or None,
            from_date=from_date,
            to_date=to_date,
        )
    except Exception:
        ctx = _yaml_events_context()
        ctx["yaml_fallback"] = True
        ctx["load_error"] = True
        return render_template("events.html", **ctx)

    if not items:
        yaml_cards = get_event_cards()
        if yaml_cards:
            ctx = _yaml_events_context()
            ctx["yaml_fallback"] = True
            ctx["empty_filter"] = bool(content_type or city or from_date or to_date)
            return render_template("events.html", **ctx)

    cards = [serialize_public_card(it) for it in items]
    json_ld = build_public_json_ld_list(items)
    canonical = canonical_events_list_url(content_type or None)

    return render_template(
        "events.html",
        events_dynamic=True,
        events=json_ld if json_ld else None,
        event_cards=cards,
        canonical_url=canonical,
        yaml_fallback=False,
        empty_filter=bool(content_type or city or from_date or to_date) and not cards,
        filter_type=content_type or None,
        filter_city=city or None,
        api_unavailable=False,
        load_error=False,
    )


@events_public_bp.route("/events/<slug>")
def events_detail(slug: str):
    if not is_events_public_ui_flag_set():
        abort(404)
    if not is_events_api_enabled():
        abort(503)

    resolved = resolve_public_item_by_slug(slug)
    if resolved is None:
        abort(404)
    if resolved.redirect_required:
        return redirect(url_for("events_public.events_detail", slug=resolved.canonical_slug), code=301)

    item = resolved.item
    detail = serialize_public_detail(item)
    json_ld = build_public_json_ld_list([item])
    base = get_public_site_base_url()
    canonical = f"{base}/events/{resolved.canonical_slug}"

    return render_template(
        "events_detail.html",
        event=detail,
        events=json_ld,
        canonical_url=canonical,
    )


@events_public_bp.route("/competitions")
def competitions_redirect():
    if not is_events_public_ui_flag_set():
        abort(404)
    if not is_events_api_enabled():
        abort(503)
    return redirect(url_for("events_page", type="competition"), code=_COMPETITIONS_REDIRECT_CODE)
