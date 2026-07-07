"""MyWave Online Coaching — public routes and apply API."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, url_for

from app.config.online_coaching_features import (
    get_online_coaching_feature_flags,
    is_online_coaching_admin_enabled,
    is_online_coaching_applications_enabled,
    is_online_coaching_channel_notify_enabled,
    is_online_coaching_enabled,
    is_online_coaching_notifications_enabled,
    is_online_coaching_tbank_api_enabled,
    is_online_coaching_telegram_video_upload_enabled,
)
from app.extensions import csrf, limiter
from app.modules.logger import get_logger
from app.services.online_coaching_notifications import notify_materials_received, notify_new_online_request
from app.services.online_coaching_channels import notify_client_channel
from app.services.online_coaching_tbank import handle_tbank_notification
from app.services.online_coaching_telegram_ingest import ingest_telegram_update, verify_telegram_webhook_secret
from app.services.online_coaching_store import (
    append_online_request,
    append_request_media,
    validate_application_payload,
    validate_media_payload,
)

logger = get_logger(__name__)

online_coaching_bp = Blueprint("online_coaching", __name__)

CONSENT_VERSION = "2026-07-v1"
_REQUEST_ID_PATH_RE = re.compile(r"^oc_req_[0-9a-f]{12,32}$", re.IGNORECASE)

_APPLY_SUCCESS_MESSAGES = {
    "video_check": (
        "Заявка принята. Следующий шаг — добавьте видео тренировки, задачу для разбора и комментарий. "
        "Оплата за разбор видео — после получения разбора."
    ),
    "progress_month": "Заявка принята. Мы свяжемся с вами для оплаты и старта подписки.",
    "live_coach_land": "Заявка принята. Мы свяжемся с вами для согласования онлайн-занятия.",
    "live_coach_water": "Заявка принята. Мы свяжемся с вами для согласования онлайн-занятия.",
}


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


def _apply_success_message(service_type: str) -> str:
    key = str(service_type or "").strip().lower()
    return _APPLY_SUCCESS_MESSAGES.get(key, "Заявка принята. Мы свяжемся с вами в выбранном канале.")


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
    # Video for video_check is submitted on the media step (PR83).
    if str(data.get("service_type") or "").strip().lower() == "video_check":
        data.pop("video_url", None)

    try:
        result = append_online_request(data)
    except ValueError as exc:
        return jsonify(ok=False, errors=[str(exc)]), 400
    except Exception as exc:
        logger.warning("online_coaching_apply_failed err=%s", exc, exc_info=True)
        return jsonify(ok=False, error="write_failed"), 500

    service_type = str(data.get("service_type") or "").strip().lower()
    show_video_step = service_type == "video_check" and result.request_status == "waiting_video"

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
                "discipline", "level", "goal", "service_type", "injuries_or_limits",
            )},
            "video_url": "",
        }
        try:
            notify_new_online_request(notify_record)
        except Exception as notify_exc:
            logger.warning(
                "online_coaching_notify_failed id=%s error=%s",
                result.online_request_id,
                str(notify_exc)[:200],
            )

    if is_online_coaching_channel_notify_enabled():
        try:
            notify_client_channel(
                {
                    "online_request_id": result.online_request_id,
                    "request_status": result.request_status,
                    **{k: data.get(k, "") for k in (
                        "name", "preferred_channel", "telegram_username", "whatsapp_phone",
                        "max_contact", "email", "phone", "service_type",
                    )},
                },
                event="application_received",
            )
        except Exception as channel_exc:
            logger.warning(
                "online_coaching_channel_notify_failed id=%s error=%s",
                result.online_request_id,
                str(channel_exc)[:200],
            )

    return jsonify(
        ok=True,
        online_request_id=result.online_request_id,
        request_status=result.request_status,
        payment_required_timing=result.payment_required_timing,
        show_video_step=show_video_step,
        message=_apply_success_message(service_type),
    ), 201


@online_coaching_bp.route("/api/online-coaching/<online_request_id>/media", methods=["POST"])
@csrf.exempt
@_apply_rate_limit()
def online_coaching_submit_media(online_request_id: str):
    if not is_online_coaching_applications_enabled():
        return jsonify(error="online_coaching_applications_disabled"), 503

    req_id = (online_request_id or "").strip()
    if not _REQUEST_ID_PATH_RE.match(req_id):
        return jsonify(ok=False, errors=["invalid:online_request_id"]), 400

    payload = request.get_json(silent=True) if request.is_json else None
    if payload is None:
        payload = request.form.to_dict(flat=True)

    errors = validate_media_payload(payload or {})
    if errors:
        return jsonify(ok=False, errors=errors), 400

    try:
        updated = append_request_media(req_id, payload or {})
    except ValueError as exc:
        code = str(exc)
        if "not_found" in code:
            return jsonify(ok=False, errors=["request_not_found"]), 404
        if "media_already_received" in code:
            return jsonify(ok=False, errors=["media_already_received"]), 409
        if "invalid_status_for_media" in code:
            return jsonify(ok=False, errors=[code]), 409
        return jsonify(ok=False, errors=[code]), 400
    except Exception as exc:
        logger.warning("online_coaching_media_failed id=%s err=%s", req_id, exc, exc_info=True)
        return jsonify(ok=False, error="write_failed"), 500

    video_urls = updated.get("video_urls") or []

    if is_online_coaching_notifications_enabled():
        try:
            notify_materials_received(updated, video_urls=video_urls)
        except Exception as notify_exc:
            logger.warning(
                "online_coaching_media_notify_failed id=%s error=%s",
                req_id,
                str(notify_exc)[:200],
            )

    if is_online_coaching_channel_notify_enabled():
        try:
            notify_client_channel(updated, event="video_received")
        except Exception as channel_exc:
            logger.warning(
                "online_coaching_channel_notify_failed id=%s error=%s",
                req_id,
                str(channel_exc)[:200],
            )

    return jsonify(
        ok=True,
        online_request_id=req_id,
        status="video_received",
        message="Видео получено",
    ), 200


@online_coaching_bp.route("/api/online-coaching/tbank/webhook", methods=["POST"])
@csrf.exempt
def online_coaching_tbank_webhook():
    if not is_online_coaching_tbank_api_enabled():
        return jsonify(error="tbank_api_disabled"), 503

    payload = request.get_json(silent=True) or {}
    try:
        result = handle_tbank_notification(payload)
    except ValueError as exc:
        code = str(exc)
        if "token" in code:
            return jsonify(error="invalid_token"), 403
        return jsonify(error=code), 400
    except Exception as exc:
        logger.warning("online_coaching_tbank_webhook_failed err=%s", exc, exc_info=True)
        return jsonify(error="webhook_failed"), 500

    return jsonify(ok=True, **{k: v for k, v in result.items() if k != "result"}), 200


@online_coaching_bp.route("/api/online-coaching/telegram/webhook", methods=["POST"])
@csrf.exempt
def online_coaching_telegram_webhook():
    if not is_online_coaching_telegram_video_upload_enabled():
        return jsonify(error="telegram_video_upload_disabled"), 503

    if not verify_telegram_webhook_secret(request.headers):
        return jsonify(error="invalid_webhook_secret"), 403

    update = request.get_json(silent=True) or {}
    try:
        result = ingest_telegram_update(update)
    except ValueError as exc:
        return jsonify(ok=False, error=str(exc)), 400
    except Exception as exc:
        logger.warning("online_coaching_telegram_ingest_failed err=%s", exc, exc_info=True)
        return jsonify(ok=False, error="ingest_failed"), 500

    if is_online_coaching_notifications_enabled():
        try:
            notify_materials_received(
                result.get("record") or {},
                video_urls=result.get("video_urls") or [],
            )
        except Exception as notify_exc:
            logger.warning(
                "online_coaching_telegram_notify_failed id=%s error=%s",
                result.get("online_request_id"),
                str(notify_exc)[:200],
            )

    if is_online_coaching_channel_notify_enabled() and result.get("record"):
        try:
            notify_client_channel(result["record"], event="video_received")
        except Exception as channel_exc:
            logger.warning(
                "online_coaching_channel_notify_failed id=%s error=%s",
                result.get("online_request_id"),
                str(channel_exc)[:200],
            )

    return jsonify(
        ok=True,
        online_request_id=result.get("online_request_id"),
        status="video_received",
    ), 200
