"""Admin UI — Social applications list and manual session assign (MVP)."""

from __future__ import annotations

from typing import Any, Dict

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.config.social_features import (
    is_social_admin_notifications_enabled,
    is_social_booking_enabled,
    is_social_module_enabled,
)
from app.services.application_notifications import notify_social_session_scheduled
from app.services.social_admin import (
    get_social_application,
    list_audit_events_for_application,
    list_social_applications,
)
from app.services.social_schema import ASSIGNABLE_APPLICATION_STATUSES
from app.services.social_sessions import manual_assign_social_session
from app.utils.decorators import admin_required

bp = Blueprint("admin_social", __name__, url_prefix="/admin/social")

_STATUS_FILTERS = ("all", "new", "review", "approved", "scheduled")
_STATUS_LABELS = {
    "all": "Все",
    "new": "Новые",
    "review": "На проверке",
    "approved": "Одобрены",
    "scheduled": "Назначены",
}
_STATUS_BADGE_CLASS = {
    "new": "admin-badge--new",
    "review": "admin-badge--review",
    "approved": "admin-badge--approved",
    "scheduled": "admin-badge--scheduled",
}


def _require_social_admin_ui() -> None:
    if not is_social_module_enabled() or not is_social_booking_enabled():
        abort(503)


def _actor_name() -> str:
    if current_user.is_authenticated:
        username = getattr(current_user, "username", None) or getattr(current_user, "email", None)
        if username:
            return str(username)[:128]
    return "admin"


@bp.route("/")
@login_required
@admin_required
def index():
    _require_social_admin_ui()
    status = (request.args.get("status") or "all").strip().lower()
    if status not in _STATUS_FILTERS:
        status = "all"
    try:
        applications = list_social_applications(
            status_filter=None if status == "all" else status,
        )
    except ValueError:
        flash("Неверный фильтр статуса.", "danger")
        return redirect(url_for("admin_social.index"))
    except Exception:
        flash("Не удалось загрузить заявки из Sheets.", "danger")
        applications = []

    return render_template(
        "admin/social/list.html",
        applications=applications,
        status_filter=status,
        status_filters=_STATUS_FILTERS,
        status_labels=_STATUS_LABELS,
        status_badge_class=_STATUS_BADGE_CLASS,
        assignable_statuses=sorted(ASSIGNABLE_APPLICATION_STATUSES),
    )


@bp.route("/<application_id>")
@login_required
@admin_required
def detail(application_id: str):
    _require_social_admin_ui()
    application = get_social_application(application_id)
    if application is None:
        flash("Заявка не найдена.", "warning")
        return redirect(url_for("admin_social.index"))

    try:
        audit_events = list_audit_events_for_application(application_id)
    except Exception:
        audit_events = []
        flash("Не удалось загрузить audit trail.", "warning")

    can_assign = application.get("status", "").lower() in ASSIGNABLE_APPLICATION_STATUSES
    return render_template(
        "admin/social/detail.html",
        application=application,
        audit_events=audit_events,
        can_assign=can_assign,
    )


@bp.route("/<application_id>/assign", methods=["GET", "POST"])
@login_required
@admin_required
def assign(application_id: str):
    _require_social_admin_ui()
    application = get_social_application(application_id)
    if application is None:
        flash("Заявка не найдена.", "warning")
        return redirect(url_for("admin_social.index"))

    status = application.get("status", "").lower()
    if status not in ASSIGNABLE_APPLICATION_STATUSES:
        flash(f"Заявка в статусе «{status}» — назначение недоступно.", "warning")
        return redirect(url_for("admin_social.detail", application_id=application_id))

    if request.method == "GET":
        return render_template(
            "admin/social/assign.html",
            application=application,
            form_data={},
        )

    form_data: Dict[str, Any] = {
        "session_date": request.form.get("session_date", "").strip(),
        "session_time": request.form.get("session_time", "").strip(),
        "location": request.form.get("location", "").strip(),
        "coach": request.form.get("coach", "").strip(),
        "service_type": request.form.get("service_type", "").strip(),
        "notes": request.form.get("notes", "").strip(),
        "assigned_by": request.form.get("assigned_by", "").strip() or _actor_name(),
    }

    if request.form.get("confirm") != "yes":
        flash("Подтвердите назначение сессии.", "warning")
        return render_template(
            "admin/social/assign.html",
            application=application,
            form_data=form_data,
            show_confirm=True,
        )

    payload = {
        "application_id": application_id,
        **form_data,
    }

    try:
        result = manual_assign_social_session(payload)
    except ValueError as exc:
        code = str(exc)
        if "not_found" in code:
            flash("Заявка не найдена в Sheets.", "danger")
        elif "not_assignable" in code or "already" in code:
            flash("Назначение недоступно для текущего статуса заявки.", "warning")
        else:
            flash("Проверьте поля формы (дата, время, локация).", "danger")
        return render_template(
            "admin/social/assign.html",
            application=application,
            form_data=form_data,
            show_confirm=True,
        )
    except Exception:
        flash("Ошибка записи в Sheets. Попробуйте позже.", "danger")
        return render_template(
            "admin/social/assign.html",
            application=application,
            form_data=form_data,
            show_confirm=True,
        )

    if is_social_admin_notifications_enabled():
        try:
            notify_social_session_scheduled(
                {
                    "application_id": result.application_id,
                    "session_id": result.session_id,
                    "session_date": result.session_date,
                    "session_time": result.session_time,
                    "location": result.location,
                    "status": result.status,
                }
            )
        except Exception:
            pass

    flash(
        f"Сессия назначена: {result.session_id} (status=scheduled).",
        "success",
    )
    return redirect(url_for("admin_social.detail", application_id=application_id))
