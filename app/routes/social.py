"""MyWave Social Mission — public routes and apply API (PR55 Social 2.0 MVP)."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

from flask import Blueprint, abort, current_app, jsonify, render_template, request

from app.config.social_features import (
    get_social_feature_flags,
    is_social_admin_notifications_enabled,
    is_social_applications_enabled,
    is_social_booking_enabled,
    is_social_module_enabled,
    is_social_public_stats_enabled,
    is_social_widget_enabled,
)
from app.extensions import csrf, limiter
from app.modules.logger import get_logger
from app.services.application_notifications import (
    notify_new_application,
    notify_social_session_scheduled,
)
from app.services.social_sessions import (
    manual_assign_social_session,
    transition_social_session_status,
    validate_assign_payload,
)
from app.services.social_stats import get_public_social_stats
from app.services.social_store import (
    append_social_application,
    validate_application_payload,
)

logger = get_logger(__name__)

social_bp = Blueprint("social", __name__)

CONSENT_VERSION = "2026-06-v1"


def _hash_client_ip() -> str:
    ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "").split(",")[0].strip()
    if not ip:
        return ""
    salt = str(current_app.config.get("SECRET_KEY") or "mywave")
    return hashlib.sha256(f"{salt}:{ip}".encode("utf-8")).hexdigest()[:24]


def _require_module() -> None:
    if not is_social_module_enabled():
        abort(404)


def build_social_notify_payload(
    application_id: str,
    data: Mapping[str, Any],
    *,
    page_url: str = "",
) -> dict[str, Any]:
    """Telegram-safe payload — no health_notes / motivation_text content."""
    health = str(data.get("health_notes") or "").strip()
    return {
        "application_id": application_id,
        "parent_name": str(data.get("parent_name") or "").strip(),
        "parent_phone": str(data.get("parent_phone") or "").strip(),
        "telegram_username": str(data.get("telegram_username") or "").strip(),
        "child_age": data.get("child_age"),
        "city": str(data.get("city") or "").strip(),
        "has_safety_info": bool(health),
        "page_url": page_url,
        "source": str(data.get("source") or "web_social_form").strip(),
        "status": "new",
    }


@social_bp.app_context_processor
def _inject_social_template_flags():
    return {
        "social_module_enabled": is_social_module_enabled(),
        "social_widget_enabled": is_social_widget_enabled(),
        "social_applications_enabled": is_social_applications_enabled(),
        "social_public_stats_enabled": is_social_public_stats_enabled(),
        "social_booking_enabled": is_social_booking_enabled(),
        "social_public_stats": get_public_social_stats() if is_social_public_stats_enabled() else None,
        "consent_version": CONSENT_VERSION,
    }


@social_bp.route("/social")
def social_page():
    _require_module()
    return render_template(
        "social/index.html",
        consent_version=CONSENT_VERSION,
        applications_enabled=is_social_applications_enabled(),
        public_stats_enabled=is_social_public_stats_enabled(),
        public_stats=get_public_social_stats() if is_social_public_stats_enabled() else None,
    )


@social_bp.route("/api/social/stats")
def social_stats_api():
    if not is_social_public_stats_enabled():
        return jsonify(error="social_stats_disabled"), 503
    stats = get_public_social_stats()
    return jsonify(ok=True, stats=stats or {})


def _apply_rate_limit():
    if limiter is None:
        return lambda f: f
    from flask_limiter.util import get_remote_address

    return limiter.limit("5 per minute", key_func=get_remote_address)


def _require_admin_token() -> bool:
    admin_token = current_app.config.get("ADMIN_TOKEN")
    if not admin_token:
        return True
    provided = request.headers.get("X-Admin-Token", "")
    return provided == admin_token


@social_bp.route("/api/social/sessions/assign", methods=["POST"])
@csrf.exempt
def social_session_assign():
    """Manual assign only — admin token + SOCIAL_BOOKING_ENABLED. No calendar auto-write."""
    if not is_social_module_enabled() or not is_social_booking_enabled():
        return jsonify(error="social_booking_disabled"), 503
    if not _require_admin_token():
        return jsonify(error="unauthorized"), 401

    payload = request.get_json(silent=True) if request.is_json else None
    if payload is None:
        payload = request.form.to_dict(flat=True)

    errors = validate_assign_payload(payload)
    if errors:
        return jsonify(ok=False, errors=errors), 400

    data = dict(payload)
    data.setdefault("assigned_by", request.headers.get("X-Actor", "admin"))

    try:
        result = manual_assign_social_session(data)
    except ValueError as exc:
        code = str(exc)
        status = 404 if "not_found" in code else 409 if "already" in code or "not_assignable" in code else 400
        return jsonify(ok=False, error=code), status
    except Exception as exc:
        logger.warning("social_session_assign_failed err=%s", exc, exc_info=True)
        return jsonify(ok=False, error="write_failed"), 500

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
        except Exception as notify_exc:
            logger.warning(
                "social_session_notify_failed session_id=%s error=%s",
                result.session_id,
                str(notify_exc)[:200],
            )

    return jsonify(
        ok=True,
        session_id=result.session_id,
        application_id=result.application_id,
        status=result.status,
        session_date=result.session_date,
        session_time=result.session_time,
        location=result.location,
    ), 201


@social_bp.route("/api/social/sessions/<session_id>/status", methods=["POST", "PATCH"])
@csrf.exempt
def social_session_status(session_id: str):
    if not is_social_module_enabled() or not is_social_booking_enabled():
        return jsonify(error="social_booking_disabled"), 503
    if not _require_admin_token():
        return jsonify(error="unauthorized"), 401

    payload = request.get_json(silent=True) if request.is_json else None
    if payload is None:
        payload = request.form.to_dict(flat=True)
    new_status = str(payload.get("status") or "").strip().lower()
    actor = str(payload.get("actor") or request.headers.get("X-Actor") or "admin").strip()

    try:
        result = transition_social_session_status(
            session_id,
            new_status,
            actor=actor,
        )
    except ValueError as exc:
        code = str(exc)
        status = 404 if "not_found" in code else 409 if "forbidden" in code or "unchanged" in code else 400
        return jsonify(ok=False, error=code), status
    except Exception as exc:
        logger.warning("social_session_status_failed err=%s", exc, exc_info=True)
        return jsonify(ok=False, error="write_failed"), 500

    return jsonify(
        ok=True,
        session_id=result.session_id,
        application_id=result.application_id,
        old_status=result.old_status,
        status=result.new_status,
    )


@social_bp.route("/api/social/apply", methods=["POST"])
@csrf.exempt
@_apply_rate_limit()
def social_apply():
    if not is_social_applications_enabled():
        return jsonify(error="social_applications_disabled"), 503

    if is_social_booking_enabled():
        logger.debug("social_apply_public_no_autobook booking_flag_on_manual_assign_only")

    payload = request.get_json(silent=True) if request.is_json else None
    if payload is None:
        payload = request.form.to_dict(flat=True)

    errors = validate_application_payload(payload)
    if errors:
        return jsonify(ok=False, errors=errors), 400

    data = dict(payload)
    data.setdefault("consent_version", CONSENT_VERSION)
    data["ip_hash"] = _hash_client_ip()
    data["source"] = "web_social_form"

    try:
        result = append_social_application(data)
    except ValueError as exc:
        return jsonify(ok=False, errors=[str(exc)]), 400
    except Exception as exc:
        logger.warning("social_apply_failed err=%s", exc, exc_info=True)
        return jsonify(ok=False, error="write_failed"), 500

    logger.info(
        "social_apply_ok",
        extra={"application_id": result.application_id, "flags": get_social_feature_flags()},
    )

    if is_social_admin_notifications_enabled():
        page_url = request.headers.get("Referer", "") or "/social"
        notify_payload = build_social_notify_payload(
            result.application_id,
            data,
            page_url=page_url,
        )
        try:
            notify_new_application("social", notify_payload)
        except Exception as notify_exc:
            logger.warning(
                "social_notify_failed application_id=%s error=%s",
                result.application_id,
                str(notify_exc)[:200],
            )

    return jsonify(
        ok=True,
        application_id=result.application_id,
        status=result.status,
        message="Заявка принята. Мы свяжемся с вами после ручной проверки и согласования безопасности.",
    ), 201
