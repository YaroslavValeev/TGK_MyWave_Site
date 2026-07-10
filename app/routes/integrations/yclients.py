"""Public YCLIENTS webhook endpoint."""

from __future__ import annotations

import hashlib
import hmac
import logging

from flask import Blueprint, jsonify, request

from app.config.yclients_config import is_yclients_enabled, yclients_webhook_secret
from app.services.booking.providers.yclients import YclientsNotConfiguredError
from app.services.booking.yclients_sync import handle_webhook_payload

logger = logging.getLogger(__name__)

bp = Blueprint("yclients_integrations", __name__)


def _verify_webhook_secret() -> bool:
    secret = yclients_webhook_secret()
    if not secret:
        return False
    provided = (
        request.headers.get("X-YCLIENTS-Webhook-Secret")
        or request.headers.get("X-Webhook-Secret")
        or ""
    ).strip()
    if not provided:
        return False
    return hmac.compare_digest(provided, secret)


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
        logger.warning("yclients_webhook_invalid", extra={"error": str(exc)})
        return jsonify({"ok": False, "error": "invalid_payload"}), 400
    except Exception:
        logger.exception("yclients_webhook_failed")
        return jsonify({"ok": False, "error": "internal_error"}), 500

    digest = hashlib.sha256(str(payload).encode("utf-8")).hexdigest()[:12]
    logger.info("yclients_webhook_ok", extra={"payload_digest": digest})
    return jsonify({"ok": True, "result": result}), 200
