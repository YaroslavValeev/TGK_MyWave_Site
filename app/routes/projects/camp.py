"""Legacy /projects/camp URLs → canonical /camps showcase."""

from __future__ import annotations

from flask import Blueprint, abort, redirect, url_for

from app.config.camp_features import is_camp_public_enabled
from app.database.models import db
from app.services.camps.repository import get_camp_by_slug

bp = Blueprint("projects_camp", __name__)


def _require_public():
    if not is_camp_public_enabled():
        abort(404)


@bp.route("/projects/camp")
def camp_index():
    _require_public()
    return redirect(url_for("camps.camps_index"), code=301)


@bp.route("/projects/camp/<slug>")
def camp_detail(slug: str):
    _require_public()
    camp = get_camp_by_slug(db.session, slug)
    if camp and camp.external_id:
        return redirect(url_for("camps.camps_detail", camp_id=camp.external_id), code=301)
    return redirect(url_for("camps.camps_index"), code=302)
