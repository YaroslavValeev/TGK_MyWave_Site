"""Health check endpoint for monitoring service status.

Checks database, cache (Redis), Sentry configuration, and optionally AI gateway.
"""

from flask import Blueprint, jsonify, current_app
import os
import time

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    """
    Enhanced health check:
    - basic status + version
    - DB check (if SQLALCHEMY_DATABASE_URI set)
    - Redis check (if REDIS_URL set)
    - Sentry DSN check (configuration presence)
    - optional AI gateway quick ping (only when ENABLE_AI_HEALTH_CHECK=1)
    """
    checks = {}
    overall_ok = True

    # Basic info
    checks["version"] = current_app.config.get("VERSION", "unknown")
    checks["mode"] = os.environ.get("MYWAVE_AI_MODE", "mock")

    # DB check
    try:
        db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI")
        if db_uri:
            try:
                from app.extensions import db

                # simple lightweight query
                res = db.session.execute("SELECT 1")
                _ = res.fetchall()
                checks["database"] = {"ok": True}
            except Exception as e:
                checks["database"] = {"ok": False, "error": str(e)}
                overall_ok = False
        else:
            checks["database"] = {
                "ok": False,
                "error": "SQLALCHEMY_DATABASE_URI not configured",
            }
            # non-fatal if app intentionally has no DB; mark as missing rather than failure
    except Exception as e:
        checks["database"] = {"ok": False, "error": f"unexpected: {e}"}
        overall_ok = False

    # Redis check
    try:
        redis_url = current_app.config.get("REDIS_URL") or current_app.config.get(
            "AI_GATEWAY_REDIS_URL"
        )
        if redis_url:
            try:
                import redis

                client = redis.Redis.from_url(redis_url, socket_connect_timeout=2)
                client.ping()
                checks["redis"] = {"ok": True}
            except Exception as e:
                checks["redis"] = {"ok": False, "error": str(e)}
                # Redis is optional, so don't mark overall as unhealthy
                # overall_ok = False
        else:
            checks["redis"] = {"ok": False, "error": "REDIS_URL not configured"}
    except ImportError:
        checks["redis"] = {"ok": False, "error": "redis package not available"}
    except Exception as e:
        checks["redis"] = {"ok": False, "error": f"unexpected: {e}"}

    # Cache check (try a set/get when cache is available)
    try:
        from app.extensions import cache

        key = f"health_check_{int(time.time())}"
        try:
            cache.set(key, "1", timeout=5)
            val = cache.get(key)
            if str(val) == "1":
                checks["cache"] = {"ok": True}
            else:
                checks["cache"] = {"ok": False, "error": "cache mismatch"}
                overall_ok = False
        except Exception as e:
            checks["cache"] = {"ok": False, "error": str(e)}
            overall_ok = False
    except Exception:
        # Cache extension missing or not configured - report as not present but non-fatal
        checks["cache"] = {"ok": False, "error": "cache extension not available"}

    # Sentry DSN check (configuration presence)
    try:
        sentry_dsn = os.getenv("SENTRY_DSN") or current_app.config.get("SENTRY_DSN")
        if sentry_dsn:
            checks["sentry"] = {"ok": True, "configured": True}
        else:
            checks["sentry"] = {
                "ok": False,
                "configured": False,
                "error": "SENTRY_DSN not configured",
            }
    except Exception as e:
        checks["sentry"] = {"ok": False, "error": f"unexpected: {e}"}

    # Optional AI gateway quick check
    try:
        enable_ai_check = os.getenv("ENABLE_AI_HEALTH_CHECK") or current_app.config.get(
            "ENABLE_AI_HEALTH_CHECK"
        )
        if str(enable_ai_check).lower() in ("1", "true", "yes"):
            try:
                from app.ai.core_gateway import create_default_gateway

                gw = create_default_gateway()
                # perform a lightweight mock ping - non-destructive
                resp = gw.handle_message("__health_ping__")
                checks["ai_gateway"] = {"ok": True, "response_type": resp.get("type")}
            except Exception as e:
                checks["ai_gateway"] = {"ok": False, "error": str(e)}
                overall_ok = False
        else:
            checks["ai_gateway"] = {"ok": False, "error": "ai health check disabled"}
    except Exception as e:
        checks["ai_gateway"] = {"ok": False, "error": f"unexpected: {e}"}

    status_code = 200 if overall_ok else 503
    return (
        jsonify(status=("ok" if overall_ok else "unhealthy"), checks=checks),
        status_code,
    )
