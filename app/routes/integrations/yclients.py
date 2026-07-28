"""Public YCLIENTS webhook + internal boat gateway endpoints."""

from __future__ import annotations

import hashlib
import hmac
import logging
from functools import wraps

from flask import Blueprint, current_app, jsonify, request

from app.config.yclients_config import (
    is_yclients_enabled,
    is_yclients_read_enabled,
    is_yclients_write_enabled,
    yclients_company_id,
    yclients_gateway_secret,
    yclients_webhook_secret,
)
from app.services.booking.providers.yclients import (
    YclientsApiError,
    YclientsNotConfiguredError,
    YclientsReadOnlyError,
    get_yclients_provider,
)
from app.services.booking.yclients_sync import handle_webhook_payload

logger = logging.getLogger(__name__)

bp = Blueprint("yclients_integrations", __name__)


def _verify_webhook_secret() -> bool:
    """YCLIENTS does not sign webhooks; we put secret in URL or custom header.

    Configure in YCLIENTS:
      https://mywavewake.ru/public/integrations/yclients/webhook?token=<SECRET>
    """
    secret = yclients_webhook_secret()
    if not secret:
        return False

    provided = (
        request.args.get("token")
        or request.args.get("secret")
        or request.headers.get("X-YCLIENTS-Webhook-Secret")
        or request.headers.get("X-Webhook-Secret")
        or ""
    ).strip()
    if not provided:
        return False
    return hmac.compare_digest(provided, secret)


def _verify_gateway_secret() -> bool:
    secret = yclients_gateway_secret()
    if not secret:
        return False
    provided = (
        request.headers.get("X-MyWave-Gateway-Secret")
        or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        or ""
    ).strip()
    if not provided:
        return False
    return hmac.compare_digest(provided, secret)


def require_gateway_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _verify_gateway_secret():
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        return fn(*args, **kwargs)

    return wrapper


@bp.route("/public/integrations/yclients/webhook", methods=["POST"])
def yclients_webhook():
    if not is_yclients_enabled():
        return jsonify({"ok": False, "error": "yclients_disabled"}), 503
    if not _verify_webhook_secret():
        logger.warning("yclients_webhook_auth_failed")
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    try:
        result = handle_webhook_payload(payload)
    except YclientsNotConfiguredError:
        return jsonify({"ok": False, "error": "yclients_disabled"}), 503
    except ValueError as exc:
        logger.warning("yclients_webhook_invalid error=%s", exc)
        return jsonify({"ok": False, "error": "invalid_payload"}), 400
    except Exception:
        logger.exception("yclients_webhook_failed")
        return jsonify({"ok": False, "error": "internal_error"}), 500

    digest = hashlib.sha256(str(payload).encode("utf-8")).hexdigest()[:12]
    logger.info("yclients_webhook_ok payload_digest=%s", digest)
    # Always 200: YCLIENTS does not retry; we still want success for their side.
    return jsonify({"ok": True, "result": result}), 200


@bp.route("/api/internal/yclients/health", methods=["GET"])
@require_gateway_auth
def yclients_health():
    return jsonify(
        {
            "ok": True,
            "enabled": is_yclients_enabled(),
            "read": is_yclients_read_enabled(),
            "write": is_yclients_write_enabled(),
            "company_id": yclients_company_id(),
        }
    )


@bp.route("/api/internal/yclients/slots", methods=["GET"])
@require_gateway_auth
def yclients_slots():
    if not is_yclients_enabled() or not is_yclients_read_enabled():
        return jsonify({"ok": False, "error": "yclients_read_disabled"}), 503
    date_str = (request.args.get("date") or "").strip()
    if not date_str:
        return jsonify({"ok": False, "error": "date_required"}), 400
    try:
        provider = get_yclients_provider()
        slots = provider.fetch_available_slots(date_str)
    except YclientsNotConfiguredError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 503
    except YclientsApiError as exc:
        return jsonify({"ok": False, "error": str(exc), "detail": exc.payload}), 502
    return jsonify(
        {
            "ok": True,
            "date": date_str,
            "slots": [
                {
                    "start_time": s.start_time,
                    "duration_minutes": s.duration_minutes,
                    "available": s.available,
                }
                for s in slots
            ],
        }
    )


@bp.route("/api/internal/yclients/bookings", methods=["POST"])
@require_gateway_auth
def yclients_create_booking():
    if not is_yclients_write_enabled():
        return jsonify({"ok": False, "error": "yclients_write_disabled"}), 503
    body = request.get_json(silent=True) or {}
    required = ("date", "time", "client_name", "client_phone")
    missing = [k for k in required if not str(body.get(k) or "").strip()]
    if missing:
        return jsonify({"ok": False, "error": "missing_fields", "fields": missing}), 400
    try:
        provider = get_yclients_provider()
        result = provider.create_booking(
            date_str=str(body["date"]).strip(),
            time_str=str(body["time"]).strip(),
            client_name=str(body["client_name"]).strip(),
            client_phone=str(body["client_phone"]).strip(),
            client_email=str(body.get("client_email") or "").strip(),
            client_surname=str(body.get("client_surname") or "").strip(),
            service_id=str(body["service_id"]).strip() if body.get("service_id") else None,
            set_count=int(body.get("set_count") or 1),
            source=str(body.get("source") or "site").strip(),
            internal_id=str(body.get("internal_id") or "").strip(),
            comment_extra=str(body.get("comment") or "").strip(),
            custom_fields=body.get("custom_fields")
            if isinstance(body.get("custom_fields"), dict)
            else None,
            datetime_iso=str(body["datetime"]).strip() if body.get("datetime") else None,
            use_online=bool(body.get("use_online", False)),
        )
    except YclientsReadOnlyError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 503
    except YclientsNotConfiguredError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 503
    except YclientsApiError as exc:
        return jsonify({"ok": False, "error": str(exc), "detail": exc.payload}), 502
    return jsonify(
        {
            "ok": True,
            "record_id": result.external_id,
            "status": result.status,
            "raw": result.raw,
        }
    ), 201


@bp.route("/api/internal/yclients/bookings/<record_id>", methods=["GET"])
@require_gateway_auth
def yclients_get_booking(record_id: str):
    if not is_yclients_read_enabled():
        return jsonify({"ok": False, "error": "yclients_read_disabled"}), 503
    try:
        provider = get_yclients_provider()
        record = provider.get_record(record_id)
    except YclientsNotConfiguredError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 503
    except YclientsApiError as exc:
        return jsonify({"ok": False, "error": str(exc), "detail": exc.payload}), 502
    return jsonify({"ok": True, "record": record})


@bp.route("/api/internal/yclients/bookings/<record_id>", methods=["PATCH"])
@require_gateway_auth
def yclients_update_booking(record_id: str):
    if not is_yclients_write_enabled():
        return jsonify({"ok": False, "error": "yclients_write_disabled"}), 503
    body = request.get_json(silent=True) or {}
    try:
        provider = get_yclients_provider()
        result = provider.update_booking(
            record_id,
            datetime_str=body.get("datetime"),
            seance_length=body.get("seance_length"),
            comment=body.get("comment"),
            attendance=body.get("attendance"),
            custom_fields=body.get("custom_fields")
            if isinstance(body.get("custom_fields"), dict)
            else None,
        )
    except YclientsReadOnlyError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 503
    except YclientsNotConfiguredError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 503
    except YclientsApiError as exc:
        return jsonify({"ok": False, "error": str(exc), "detail": exc.payload}), 502

    mirror = None
    try:
        from app.services.booking.yclients_sync import sync_record_to_calendar
        from app.config.yclients_config import yclients_company_id

        full = provider.get_record(record_id) or {}
        mirror = sync_record_to_calendar(
            {
                "company_id": yclients_company_id(),
                "record_id": str(record_id),
                "id": str(record_id),
                "attendance": full.get("attendance"),
                "datetime": full.get("datetime") or full.get("date") or body.get("datetime"),
                "seance_length": full.get("seance_length") or full.get("length"),
                "comment": full.get("comment") or "",
                "client": full.get("client") or {},
                "services": full.get("services") or [],
                "staff_id": full.get("staff_id"),
                "deleted": bool(full.get("deleted")),
            }
        )
    except Exception as exc:
        current_app.logger.warning(
            "yclients_patch_mirror_failed record_id=%s err=%s",
            record_id,
            type(exc).__name__,
        )

    return jsonify(
        {
            "ok": True,
            "record_id": result.external_id,
            "status": result.status,
            "raw": result.raw,
            "mirror": (mirror or {}).get("mirror") if isinstance(mirror, dict) else None,
        }
    )


@bp.route("/api/internal/yclients/bookings/<record_id>/cancel", methods=["POST"])
@require_gateway_auth
def yclients_cancel_booking(record_id: str):
    if not is_yclients_write_enabled():
        return jsonify({"ok": False, "error": "yclients_write_disabled"}), 503
    try:
        provider = get_yclients_provider()
        provider.cancel_booking(record_id)
    except YclientsReadOnlyError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 503
    except YclientsNotConfiguredError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 503
    except YclientsApiError as exc:
        return jsonify({"ok": False, "error": str(exc), "detail": exc.payload}), 502

    sheets = {}
    try:
        from app.services.booking.sheets_writer import mark_yclients_journal_cancelled

        sheets = mark_yclients_journal_cancelled(record_id)
    except Exception as exc:
        current_app.logger.warning(
            "yclients_cancel_sheets_failed record_id=%s err=%s",
            record_id,
            type(exc).__name__,
        )

    mirror = None
    try:
        from app.services.booking.yclients_sync import sync_record_to_calendar
        from app.config.yclients_config import yclients_company_id

        mirror = sync_record_to_calendar(
            {
                "company_id": yclients_company_id(),
                "record_id": str(record_id),
                "id": str(record_id),
                "attendance": -1,
                "lifecycle": "cancelled",
                "deleted": False,
            }
        )
    except Exception as exc:
        current_app.logger.warning(
            "yclients_cancel_mirror_failed record_id=%s err=%s",
            record_id,
            type(exc).__name__,
        )

    return jsonify(
        {
            "ok": True,
            "record_id": record_id,
            "status": "cancelled",
            "sheets": sheets,
            "mirror": (mirror or {}).get("mirror") if isinstance(mirror, dict) else None,
        }
    )
