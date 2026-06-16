"""MyWave Social Mission — public routes and apply API (Social-2/4 staging UI)."""

from __future__ import annotations

import hashlib

from flask import Blueprint, abort, current_app, jsonify, render_template, request

from app.config.social_features import (
    get_social_feature_flags,
    is_social_applications_enabled,
    is_social_module_enabled,
    is_social_public_stats_enabled,
    is_social_widget_enabled,
)
from app.extensions import csrf, limiter
from app.modules.logger import get_logger
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


@social_bp.app_context_processor
def _inject_social_template_flags():
    return {
        "social_module_enabled": is_social_module_enabled(),
        "social_widget_enabled": is_social_widget_enabled(),
        "social_applications_enabled": is_social_applications_enabled(),
        "social_public_stats": get_public_social_stats() if is_social_public_stats_enabled() else None,
    }


@social_bp.route("/social")
def social_page():
    _require_module()
    return render_template(
        "social/index.html",
        consent_version=CONSENT_VERSION,
        applications_enabled=is_social_applications_enabled(),
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


@social_bp.route("/api/social/apply", methods=["POST"])
@csrf.exempt
@_apply_rate_limit()
def social_apply():
    if not is_social_applications_enabled():
        return jsonify(error="social_applications_disabled"), 503

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
    return jsonify(
        ok=True,
        application_id=result.application_id,
        status=result.status,
        message="Заявка принята. Мы свяжемся с вами после рассмотрения.",
    ), 201
