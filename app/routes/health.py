"""Health endpoints for monitoring: liveness, readiness, and aggregate status."""
from __future__ import annotations

import os
import time
from typing import Any, Dict, Tuple

from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

health_bp = Blueprint("health", __name__)

_OPTIONAL_KEYS = ("redis", "cache", "sentry", "google", "ai_gateway")


def _mask_id(value: str | None) -> str:
    raw = (value or "").strip()
    if len(raw) <= 8:
        return "unset" if not raw else "***"
    return f"{raw[:4]}…{raw[-4:]}"


def _skipped_optional(*, error: str, configured: bool | None = None) -> Dict[str, Any]:
    """Optional dependency not configured or explicitly disabled — not a failure."""
    out: Dict[str, Any] = {
        "ok": True,
        "optional": True,
        "skipped": True,
        "error": error,
    }
    if configured is not None:
        out["configured"] = configured
    return out


def _google_credentials_path() -> str | None:
    for key in (
        "GOOGLE_SERVICE_ACCOUNT_FILE",
        "GOOGLE_SHEETS_CREDENTIALS",
        "GOOGLE_APPLICATION_CREDENTIALS",
    ):
        val = (current_app.config.get(key) or os.getenv(key) or "").strip()
        if val:
            return val
    return None


def _check_database() -> Dict[str, Any]:
    """Ping DB via the same SQLAlchemy instance as models (app.database.models.db)."""
    db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI")
    if not db_uri:
        return {"ok": False, "critical": True, "error": "SQLALCHEMY_DATABASE_URI not configured"}
    try:
        from app.database.models import db

        db.session.execute(text("SELECT 1"))
        return {"ok": True, "critical": True}
    except Exception as exc:
        return {"ok": False, "critical": True, "error": str(exc)}


def _check_redis() -> Dict[str, Any]:
    redis_url = (
        current_app.config.get("REDIS_URL")
        or current_app.config.get("AI_GATEWAY_REDIS_URL")
        or os.getenv("REDIS_URL")
    )
    if not redis_url:
        return _skipped_optional(error="REDIS_URL not configured", configured=False)
    try:
        import redis

        client = redis.Redis.from_url(redis_url, socket_connect_timeout=2)
        client.ping()
        return {"ok": True, "optional": True, "configured": True}
    except Exception as exc:
        return {"ok": False, "optional": True, "configured": True, "error": str(exc)}


def _check_cache() -> Dict[str, Any]:
    try:
        from app.extensions import cache

        key = f"health_check_{int(time.time())}"
        cache.set(key, "1", timeout=5)
        val = cache.get(key)
        if str(val) == "1":
            return {"ok": True, "optional": True}
        return {"ok": False, "optional": True, "error": "cache mismatch"}
    except Exception as exc:
        return {"ok": False, "optional": True, "error": str(exc)}


def _check_sentry() -> Dict[str, Any]:
    sentry_dsn = os.getenv("SENTRY_DSN") or current_app.config.get("SENTRY_DSN")
    if sentry_dsn:
        return {"ok": True, "optional": True, "configured": True}
    return _skipped_optional(error="SENTRY_DSN not configured", configured=False)


def _check_google() -> Dict[str, Any]:
    path = _google_credentials_path()
    if not path:
        return _skipped_optional(error="credentials path not set", configured=False)
    if os.path.isfile(path):
        return {"ok": True, "optional": True, "configured": True}
    return {"ok": False, "optional": True, "configured": True, "error": "service account file missing"}


def _check_ai_gateway() -> Dict[str, Any]:
    enable = os.getenv("ENABLE_AI_HEALTH_CHECK") or current_app.config.get("ENABLE_AI_HEALTH_CHECK")
    if str(enable).lower() not in ("1", "true", "yes"):
        return _skipped_optional(error="ai health check disabled")
    try:
        from app.ai.core_gateway import create_default_gateway

        gw = create_default_gateway()
        resp = gw.handle_message("__health_ping__")
        return {"ok": True, "optional": True, "response_type": resp.get("type")}
    except Exception as exc:
        return {"ok": False, "optional": True, "error": str(exc)}


def _collect_checks() -> Dict[str, Any]:
    checks: Dict[str, Any] = {
        "version": current_app.config.get("VERSION", "unknown"),
        "mode": os.environ.get("MYWAVE_AI_MODE", "mock"),
        "spreadsheet_id": _mask_id(current_app.config.get("SPREADSHEET_ID")),
    }
    checks["database"] = _check_database()
    checks["redis"] = _check_redis()
    checks["cache"] = _check_cache()
    checks["sentry"] = _check_sentry()
    checks["google"] = _check_google()
    checks["ai_gateway"] = _check_ai_gateway()
    return checks


def _optional_causes_degraded(check: Dict[str, Any]) -> bool:
    if check.get("skipped"):
        return False
    return not check.get("ok", False)


def _health_payload(*, readiness: bool = False) -> Tuple[dict, int]:
    checks = _collect_checks()
    critical_ok = checks["database"].get("ok", False)

    if not critical_ok:
        status = "unhealthy"
        code = 503
    elif readiness:
        status = "ok"
        code = 200
    elif any(_optional_causes_degraded(checks[k]) for k in _OPTIONAL_KEYS):
        status = "degraded"
        code = 200
    else:
        status = "ok"
        code = 200

    return {"status": status, "checks": checks}, code


@health_bp.route("/health/live", methods=["GET"])
@health_bp.route("/api/health/live", methods=["GET"])
def health_live():
    return jsonify(status="ok", live=True), 200


@health_bp.route("/health/ready", methods=["GET"])
@health_bp.route("/api/health/ready", methods=["GET"])
def health_ready():
    payload, code = _health_payload(readiness=True)
    return jsonify(payload), code


@health_bp.route("/health", methods=["GET"])
@health_bp.route("/api/health", methods=["GET"])
def health_check():
    payload, code = _health_payload(readiness=False)
    return jsonify(payload), code
