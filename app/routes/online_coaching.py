"""MyWave Online Coaching — public routes and apply API."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, url_for

from app.config.online_coaching_features import (
    get_online_coaching_feature_flags,
    is_online_coaching_admin_enabled,
    is_online_coaching_applications_enabled,
    is_online_coaching_enabled,
    is_online_coaching_notifications_enabled,
)
from app.extensions import csrf, limiter
from app.modules.logger import get_logger
from app.services.online_coaching_notifications import notify_new_online_request
from app.services.online_coaching_store import append_online_request, validate_application_payload

logger = get_logger(__name__)

online_coaching_bp = Blueprint("online_coaching", __name__)

CONSENT_VERSION = "2026-07-v1"


def _hash_client_ip() -> str:
    ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "").split(",")[0].strip()
    if not ip:
        return ""
    salt = str(current_app.config.get("SECRET_KEY") or "mywave")
    return hashlib.sha256(f"{salt}:{ip}".encode("utf-8")).hexdigest()[:24]


def _require_module() -> None:
    if not is_online_coaching_enabled():
        abort(404)


@online_coaching_bp.app_context_processor
def _inject_online_coaching_flags():
    return {
        "online_coaching_enabled": is_online_coaching_enabled(),
        "online_coaching_applications_enabled": is_online_coaching_applications_enabled(),
        "online_coaching_admin_enabled": is_online_coaching_admin_enabled(),
        "online_coaching_consent_version": CONSENT_VERSION,
    }


@online_coaching_bp.route("/services/online-coaching")
def online_coaching_page():
    _require_module()
    return render_template(
        "services/online_coaching.html",
        consent_version=CONSENT_VERSION,
        applications_enabled=is_online_coaching_applications_enabled(),
    )


@online_coaching_bp.route("/online-coaching")
def online_coaching_short_redirect():
    _require_module()
    return redirect(url_for("online_coaching.online_coaching_page"), code=302)


def _apply_rate_limit():
    if limiter is None:
        return lambda f: f
    from flask_limiter.util import get_remote_address

    return limiter.limit("5 per minute", key_func=get_remote_address)


@online_coaching_bp.route("/api/online-coaching/apply", methods=["POST"])
@csrf.exempt
@_apply_rate_limit()
def online_coaching_apply():
    if not is_online_coaching_applications_enabled():
        return jsonify(error="online_coaching_applications_disabled"), 503

    payload = request.get_json(silent=True) if request.is_json else None
    if payload is None:
        payload = request.form.to_dict(flat=True)

    errors = validate_application_payload(payload)
    if errors:
        return jsonify(ok=False, errors=errors), 400

    data = dict(payload)
    data.setdefault("consent_version", CONSENT_VERSION)
    data["ip_hash"] = _hash_client_ip()
    data.setdefault("source", "web_online_coaching")

    try:
        result = append_online_request(data)
    except ValueError as exc:
        return jsonify(ok=False, errors=[str(exc)]), 400
    except Exception as exc:
        logger.warning("online_coaching_apply_failed err=%s", exc, exc_info=True)
        return jsonify(ok=False, error="write_failed"), 500

    logger.info(
        "online_coaching_apply_ok",
        extra={"online_request_id": result.online_request_id, "flags": get_online_coaching_feature_flags()},
    )

    if is_online_coaching_notifications_enabled():
        notify_record = {
            "online_request_id": result.online_request_id,
            "request_status": result.request_status,
            "payment_required_timing": result.payment_required_timing,
            **{k: data.get(k, "") for k in (
                "name", "phone", "email", "preferred_channel", "telegram_username",
                "discipline", "level", "goal", "video_url", "service_type",
                "injuries_or_limits",
            )},
        }
        try:
            notify_new_online_request(notify_record)
        except Exception as notify_exc:
            logger.warning(
                "online_coaching_notify_failed id=%s error=%s",
                result.online_request_id,
                str(notify_exc)[:200],
            )

    return jsonify(
        ok=True,
        online_request_id=result.online_request_id,
        request_status=result.request_status,
        payment_required_timing=result.payment_required_timing,
        message="Заявка принята. Мы свяжемся с вами в выбранном канале.",
    ), 201
