"""Admin UI — MyWave Online Coaching requests."""

from __future__ import annotations

from typing import Any, Dict

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.config.online_coaching_features import (
    is_online_coaching_admin_enabled,
    is_online_coaching_enabled,
    is_online_coaching_notifications_enabled,
)
from app.services.online_coaching_admin import get_online_request, get_online_request_detail, list_online_requests
from app.services.online_coaching_notifications import (
    notify_payment_needed,
    notify_review_ready,
    notify_review_sent,
    notify_subscription_paid,
    notify_video_received,
)
from app.services.online_coaching_payments import mark_paid, record_manual_payment_url
from app.services.online_coaching_schema import REQUEST_STATUSES, SERVICE_TYPES, STATUSES_BY_SERVICE, service_display_name
from app.services.online_coaching_store import append_diary_entry, append_followup, log_admin_action, update_request_fields
from app.utils.decorators import admin_required

bp = Blueprint("admin_online_coaching", __name__, url_prefix="/admin/online-coaching")


@bp.app_context_processor
def _inject_oc_service_labels():
    from app.services.online_coaching_schema import SERVICE_DISPLAY_NAMES

    return {
        "oc_service_label": service_display_name,
        "oc_service_labels": SERVICE_DISPLAY_NAMES,
    }


_STATUS_FILTERS = (
    "all", "new", "waiting_video", "waiting_payment", "paid", "subscription_active",
    "in_review", "review_ready", "completed",
)
_STATUS_LABELS = {
    "all": "Все",
    "new": "Новые",
    "waiting_video": "Ждём видео",
    "waiting_payment": "Ждём оплату",
    "paid": "Оплачено",
    "subscription_active": "Подписка активна",
    "in_review": "В разборе",
    "review_ready": "Разбор готов",
    "completed": "Завершено",
}


def _require_admin_ui() -> None:
    if not is_online_coaching_enabled() or not is_online_coaching_admin_enabled():
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
    _require_admin_ui()
    status = (request.args.get("status") or "all").strip().lower()
    if status not in _STATUS_FILTERS:
        status = "all"
    try:
        requests_rows = list_online_requests(status_filter=None if status == "all" else status)
    except ValueError:
        flash("Неверный фильтр статуса.", "danger")
        return redirect(url_for("admin_online_coaching.index"))
    except Exception:
        flash("Не удалось загрузить заявки из Sheets.", "danger")
        requests_rows = []

    return render_template(
        "admin/online_coaching/list.html",
        requests=requests_rows,
        status_filter=status,
        status_filters=_STATUS_FILTERS,
        status_labels=_STATUS_LABELS,
        service_types=sorted(SERVICE_TYPES),
    )


@bp.route("/<online_request_id>")
@login_required
@admin_required
def detail(online_request_id: str):
    _require_admin_ui()
    record = get_online_request_detail(online_request_id)
    if record is None:
        flash("Заявка не найдена.", "warning")
        return redirect(url_for("admin_online_coaching.index"))

    service_type = record.get("service_type", "")
    status_options = STATUSES_BY_SERVICE.get(service_type, tuple(sorted(REQUEST_STATUSES)))

    return render_template(
        "admin/online_coaching/detail.html",
        request_record=record,
        request_statuses=status_options,
    )


@bp.route("/<online_request_id>/status", methods=["POST"])
@login_required
@admin_required
def change_status(online_request_id: str):
    _require_admin_ui()
    new_status = (request.form.get("status") or "").strip().lower()
    if new_status not in REQUEST_STATUSES:
        flash("Недопустимый статус.", "danger")
        return redirect(url_for("admin_online_coaching.detail", online_request_id=online_request_id))

    try:
        prev = get_online_request_detail(online_request_id) or {}
        updated = update_request_fields(online_request_id, {"request_status": new_status})
    except ValueError as exc:
        if "not_found" in str(exc):
            flash("Заявка не найдена.", "warning")
        else:
            flash("Не удалось обновить статус.", "danger")
        return redirect(url_for("admin_online_coaching.detail", online_request_id=online_request_id))
    except Exception:
        flash("Ошибка записи в Sheets.", "danger")
        return redirect(url_for("admin_online_coaching.detail", online_request_id=online_request_id))

    log_admin_action(
        online_request_id,
        actor=_actor_name(),
        action="status_change",
        summary=f"{prev.get('request_status', '—')} -> {new_status}",
        client_id=prev.get("client_id", ""),
    )

    if is_online_coaching_notifications_enabled():
        try:
            if new_status == "video_received":
                notify_video_received(updated)
            elif new_status == "review_ready":
                notify_review_ready(updated)
            elif new_status == "review_sent":
                notify_review_sent(updated)
            elif new_status == "waiting_payment":
                notify_payment_needed(updated)
        except Exception:
            pass

    flash(f"Статус обновлён: {new_status}", "success")
    return redirect(url_for("admin_online_coaching.detail", online_request_id=online_request_id))


@bp.route("/<online_request_id>/payment", methods=["POST"])
@login_required
@admin_required
def save_payment_url(online_request_id: str):
    _require_admin_ui()
    url = (request.form.get("tbank_payment_url") or request.form.get("payment_url") or "").strip()
    amount_raw = (request.form.get("amount") or "").strip()
    amount = float(amount_raw) if amount_raw else None

    try:
        record_manual_payment_url(online_request_id, url, amount)
        log_admin_action(online_request_id, actor=_actor_name(), action="payment_url_saved", summary="tbank_link")
    except ValueError as exc:
        code = str(exc)
        if "not_found" in code:
            flash("Заявка не найдена.", "warning")
        elif "payment_url" in code:
            flash("Укажите ссылку на оплату.", "danger")
        else:
            flash("Не удалось сохранить ссылку.", "danger")
        return redirect(url_for("admin_online_coaching.detail", online_request_id=online_request_id))
    except Exception:
        flash("Ошибка записи в Sheets.", "danger")
        return redirect(url_for("admin_online_coaching.detail", online_request_id=online_request_id))

    flash("Ссылка на оплату сохранена.", "success")
    return redirect(url_for("admin_online_coaching.detail", online_request_id=online_request_id))


@bp.route("/<online_request_id>/mark-paid", methods=["POST"])
@login_required
@admin_required
def mark_paid_action(online_request_id: str):
    _require_admin_ui()
    amount_raw = (request.form.get("amount") or "").strip()
    amount = float(amount_raw) if amount_raw else None

    try:
        result = mark_paid(online_request_id, amount=amount)
        log_admin_action(online_request_id, actor=_actor_name(), action="mark_paid", summary=str(result.get("amount")))
    except ValueError as exc:
        if "not_found" in str(exc):
            flash("Заявка не найдена.", "warning")
        else:
            flash("Не удалось отметить оплату.", "danger")
        return redirect(url_for("admin_online_coaching.detail", online_request_id=online_request_id))
    except Exception:
        flash("Ошибка записи в Sheets.", "danger")
        return redirect(url_for("admin_online_coaching.detail", online_request_id=online_request_id))

    if is_online_coaching_notifications_enabled():
        record = result.get("request") or {}
        if record.get("service_type") == "progress_month":
            try:
                notify_subscription_paid(record)
            except Exception:
                pass

    flash("Оплата отмечена.", "success")
    return redirect(url_for("admin_online_coaching.detail", online_request_id=online_request_id))


@bp.route("/<online_request_id>/diary", methods=["POST"])
@login_required
@admin_required
def add_diary_entry(online_request_id: str):
    _require_admin_ui()
    entry: Dict[str, Any] = {
        "date": request.form.get("date", "").strip(),
        "current_goal": request.form.get("current_goal", "").strip(),
        "main_mistake": request.form.get("main_mistake", "").strip(),
        "water_task": request.form.get("water_task", "").strip(),
        "land_task": request.form.get("land_task", "").strip(),
        "ofp_task": request.form.get("ofp_task", "").strip(),
        "related_discipline_task": request.form.get("related_discipline_task", "").strip(),
        "next_video_request": request.form.get("next_video_request", "").strip(),
        "trainer_notes": request.form.get("trainer_notes", "").strip(),
        "diary_url": request.form.get("diary_url", "").strip(),
        "status": request.form.get("status", "active").strip() or "active",
    }

    try:
        diary_id = append_diary_entry(online_request_id, entry)
        log_admin_action(online_request_id, actor=_actor_name(), action="diary_entry", summary=diary_id)
    except ValueError as exc:
        if "not_found" in str(exc):
            flash("Заявка не найдена.", "warning")
        else:
            flash("Не удалось сохранить запись дневника.", "danger")
        return redirect(url_for("admin_online_coaching.detail", online_request_id=online_request_id))
    except Exception:
        flash("Ошибка записи в Sheets.", "danger")
        return redirect(url_for("admin_online_coaching.detail", online_request_id=online_request_id))

    flash(f"Запись дневника создана: {diary_id}", "success")
    return redirect(url_for("admin_online_coaching.detail", online_request_id=online_request_id))


@bp.route("/<online_request_id>/followup", methods=["POST"])
@login_required
@admin_required
def add_followup(online_request_id: str):
    _require_admin_ui()
    entry: Dict[str, Any] = {
        "scheduled_at": request.form.get("scheduled_at", "").strip(),
        "channel": request.form.get("channel", "").strip(),
        "note": request.form.get("note", "").strip(),
        "status": request.form.get("status", "scheduled").strip() or "scheduled",
    }

    try:
        followup_id = append_followup(online_request_id, entry)
        log_admin_action(online_request_id, actor=_actor_name(), action="followup", summary=followup_id)
    except ValueError as exc:
        if "not_found" in str(exc):
            flash("Заявка не найдена.", "warning")
        else:
            flash("Не удалось сохранить follow-up.", "danger")
        return redirect(url_for("admin_online_coaching.detail", online_request_id=online_request_id))
    except Exception:
        flash("Ошибка записи в Sheets.", "danger")
        return redirect(url_for("admin_online_coaching.detail", online_request_id=online_request_id))

    flash(f"Follow-up запланирован: {followup_id}", "success")
    return redirect(url_for("admin_online_coaching.detail", online_request_id=online_request_id))
