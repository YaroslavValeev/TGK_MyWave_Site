"""Public pages: /projects/camp."""

from __future__ import annotations

from flask import Blueprint, abort, render_template, request

from app.config.camp_features import is_camp_public_enabled
from app.database.models import db
from app.services.camps.public import camp_to_api_dict, get_effective_camp
from app.services.camps.repository import get_camp_by_slug, get_similar_camps, list_public_camps
from app.services.camps.seo import build_camp_seo, camp_json_ld_script

bp = Blueprint("projects_camp", __name__)


def _require_public():
    if not is_camp_public_enabled():
        abort(404)


@bp.route("/projects/camp")
def camp_index():
    _require_public()
    filters = {
        "sport": request.args.get("sport"),
        "level": request.args.get("level"),
        "country": request.args.get("country"),
        "availability": request.args.get("availability"),
        "price_max": request.args.get("price_max"),
        "month": request.args.get("month"),
    }
    camps = list_public_camps(db.session, {k: v for k, v in filters.items() if v})
    cards = [get_effective_camp(c) for c in camps]
    return render_template(
        "projects/camp/index.html",
        camps=cards,
        filters=filters,
        seo={
            "title": "Вейксерф и вейкборд кемпы — MyWave",
            "meta_description": "Актуальные кемпы по вейксерфингу и вейкборду для русскоязычной аудитории. MyWave Camp и партнёрские программы.",
            "robots": "index,follow",
        },
    )


@bp.route("/projects/camp/<slug>")
def camp_detail(slug: str):
    _require_public()
    camp = get_camp_by_slug(db.session, slug)
    if not camp:
        abort(404)
    if camp.publication_status not in ("published", "archived"):
        abort(404)
    eff = get_effective_camp(camp)
    similar = [get_effective_camp(c) for c in get_similar_camps(db.session, camp)]
    seo = build_camp_seo(camp)
    return render_template(
        "projects/camp/detail.html",
        camp=eff,
        similar=similar,
        seo=seo,
        json_ld=camp_json_ld_script(camp),
        is_archived=camp.publication_status == "archived",
    )
