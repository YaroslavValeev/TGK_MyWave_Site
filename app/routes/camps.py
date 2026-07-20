"""Public camp showcase pages: /camps (Tour Camp API, server-side only)."""

from __future__ import annotations

from flask import Blueprint, abort, render_template, url_for

from app.config.camp_features import is_camp_public_enabled
from app.services.camps.showcase import fetch_showcase_camps, fetch_showcase_detail

camps_bp = Blueprint("camps", __name__)

CAMP_COVER_FALLBACK = "images/Place1Logo.png"


def _require_public():
    if not is_camp_public_enabled():
        abort(404)


@camps_bp.app_context_processor
def _inject_camp_nav_flags():
    return {
        "camp_public_enabled": is_camp_public_enabled(),
        "camp_cover_fallback": CAMP_COVER_FALLBACK,
    }


@camps_bp.route("/camps")
def camps_index():
    _require_public()
    result = fetch_showcase_camps()
    status_code = 200
    if result.state.startswith("error_"):
        status_code = 503 if result.state == "error_server" else 502
    return (
        render_template(
            "camps/index.html",
            camps=result.camps,
            page_state=result.state,
            page_message=result.message,
            cover_fallback=CAMP_COVER_FALLBACK,
            seo={
                "title": "Кемпы — MyWave",
                "meta_description": "Актуальные вейксерф и вейкборд кемпы для русскоязычной аудитории.",
                "robots": "index,follow" if result.state == "ok" else "noindex,follow",
            },
        ),
        status_code,
    )


@camps_bp.route("/camps/<camp_id>")
def camps_detail(camp_id: str):
    _require_public()
    result = fetch_showcase_detail(camp_id)
    if result.state == "not_found":
        abort(404)
    if result.state.startswith("error_"):
        status_code = 503 if result.state == "error_server" else 502
        return (
            render_template(
                "camps/error.html",
                page_state=result.state,
                page_message=result.message,
                seo={
                    "title": "Кемпы — временно недоступны — MyWave",
                    "meta_description": "Каталог кемпов временно недоступен.",
                    "robots": "noindex,follow",
                },
            ),
            status_code,
        )

    camp = result.camp or {}
    return render_template(
        "camps/detail.html",
        camp=camp,
        cover_fallback=CAMP_COVER_FALLBACK,
        seo={
            "title": f"{camp.get('title') or 'Кемп'} — MyWave",
            "meta_description": camp.get("short_description") or camp.get("description") or "Кемп MyWave",
            "robots": "index,follow",
            "canonical_url": url_for("camps.camps_detail", camp_id=camp.get("id"), _external=True),
        },
    )
