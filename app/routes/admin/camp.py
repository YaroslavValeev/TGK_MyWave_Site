"""Admin UI for Camp catalog."""

from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.config.camp_features import is_camp_admin_enabled, is_camp_import_enabled
from app.database.camp_models import Camp, CampImportLog
from app.database.models import db
from app.services.camps.import_service import sync_camps_from_tour
from app.services.camps.schema import PUBLICATION_STATUS_LABELS, PUBLICATION_STATUSES
from app.utils.decorators import admin_required

bp = Blueprint("admin_camp", __name__, url_prefix="/admin/camp")


@bp.app_context_processor
def _inject_camp_flags():
    from app.config.camp_features import is_camp_admin_enabled, is_camp_module_enabled

    return {
        "camp_module_enabled": is_camp_module_enabled(),
        "camp_admin_enabled": is_camp_admin_enabled(),
    }


def _require_admin():
    if not is_camp_admin_enabled():
        abort(503)


@bp.route("/")
@login_required
@admin_required
def index():
    _require_admin()
    status = request.args.get("status", "all")
    q = db.session.query(Camp).order_by(Camp.updated_at.desc())
    if status != "all" and status in PUBLICATION_STATUSES:
        q = q.filter(Camp.publication_status == status)
    camps = q.limit(200).all()
    logs = (
        db.session.query(CampImportLog)
        .order_by(CampImportLog.started_at.desc())
        .limit(20)
        .all()
    )
    return render_template(
        "admin/camp/list.html",
        camps=camps,
        logs=logs,
        status=status,
        status_labels=PUBLICATION_STATUS_LABELS,
        import_enabled=is_camp_import_enabled(),
    )


@bp.route("/<int:camp_id>")
@login_required
@admin_required
def detail(camp_id: int):
    _require_admin()
    camp = db.session.get(Camp, camp_id)
    if not camp:
        abort(404)
    return render_template("admin/camp/detail.html", camp=camp, status_labels=PUBLICATION_STATUS_LABELS)


@bp.route("/<int:camp_id>/publish", methods=["POST"])
@login_required
@admin_required
def publish(camp_id: int):
    _require_admin()
    camp = db.session.get(Camp, camp_id)
    if not camp:
        abort(404)
    camp.publication_status = "published"
    camp.robots_index = True
    db.session.commit()
    flash("Кемп опубликован.", "success")
    return redirect(url_for("admin_camp.detail", camp_id=camp_id))


@bp.route("/<int:camp_id>/hide", methods=["POST"])
@login_required
@admin_required
def hide(camp_id: int):
    _require_admin()
    camp = db.session.get(Camp, camp_id)
    if not camp:
        abort(404)
    camp.publication_status = "hidden"
    camp.robots_index = False
    db.session.commit()
    flash("Кемп скрыт.", "success")
    return redirect(url_for("admin_camp.detail", camp_id=camp_id))


@bp.route("/sync", methods=["POST"])
@login_required
@admin_required
def sync_now():
    _require_admin()
    if not is_camp_import_enabled():
        abort(503)
    try:
        stats = sync_camps_from_tour()
        flash(f"Синхронизация завершена: {stats}", "success")
    except Exception as exc:
        flash(f"Ошибка синхронизации: {exc}", "error")
    return redirect(url_for("admin_camp.index"))
