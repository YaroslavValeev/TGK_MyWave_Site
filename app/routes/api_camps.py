"""JSON API for Camp catalog and leads."""

from __future__ import annotations

from flask import Blueprint, abort, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.config.camp_features import is_camp_public_enabled
from app.database.camp_models import CampLead
from app.database.models import db
from app.services.camps.notifications import notify_camp_lead
from app.services.camps.public import camp_to_api_dict
from app.services.camps.repository import get_camp_by_slug, list_public_camps

api_camps_bp = Blueprint("api_camps", __name__, url_prefix="/api/camps")


def _require_api():
    if not is_camp_public_enabled():
        abort(404)


@api_camps_bp.route("", methods=["GET"])
@api_camps_bp.route("/", methods=["GET"])
def api_camps_list():
    _require_api()
    filters = {
        "sport": request.args.get("sport"),
        "level": request.args.get("level"),
        "country": request.args.get("country"),
        "availability": request.args.get("availability"),
        "price_max": request.args.get("price_max"),
        "month": request.args.get("month"),
    }
    camps = list_public_camps(db.session, {k: v for k, v in filters.items() if v})
    return jsonify({"success": True, "camps": [camp_to_api_dict(c) for c in camps]})


@api_camps_bp.route("/<slug>", methods=["GET"])
def api_camp_detail(slug: str):
    _require_api()
    camp = get_camp_by_slug(db.session, slug)
    if not camp or camp.publication_status not in ("published", "archived"):
        abort(404)
    return jsonify({"success": True, "camp": camp_to_api_dict(camp)})


@api_camps_bp.route("/<int:camp_id>/lead", methods=["POST"])
def api_camp_lead(camp_id: int):
    _require_api()
    from app.database.camp_models import Camp as CampModel

    camp = db.session.get(CampModel, camp_id)
    if not camp or camp.publication_status != "published":
        abort(404)
    data = request.get_json(silent=True) or {}
    name = str(data.get("name") or "").strip()
    phone = str(data.get("phone") or "").strip()
    if not name or not phone:
        return jsonify({"success": False, "error": "name_and_phone_required"}), 400
    lead = CampLead(
        camp_id=camp.id,
        name=name[:200],
        phone=phone[:64],
        telegram=str(data.get("telegram") or "").strip()[:128] or None,
        level=str(data.get("level") or "").strip()[:64] or None,
        comment=str(data.get("comment") or "").strip()[:2000] or None,
    )
    db.session.add(lead)
    db.session.commit()
    try:
        if notify_camp_lead(camp, data):
            lead.notification_status = "sent"
        else:
            lead.notification_status = "failed"
    except Exception:
        lead.notification_status = "failed"
    db.session.commit()
    return jsonify({"success": True, "lead_id": lead.id}), 201
