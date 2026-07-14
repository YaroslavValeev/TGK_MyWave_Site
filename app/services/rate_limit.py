"""Rate-limit helpers: client IP behind Nginx, public-route filter, 429 responses."""

from __future__ import annotations

from typing import Callable, Iterable, Optional, TypeVar

from flask import Request, jsonify, request
from flask_limiter.util import get_remote_address

F = TypeVar("F", bound=Callable)

_PUBLIC_GET_PREFIXES = (
    "/static/",
    "/health",
    "/api/health",
    "/robots.txt",
    "/sitemap.xml",
    "/favicon.ico",
)

_PUBLIC_GET_EXACT = frozenset({
    "/",
    "/health",
    "/health/live",
    "/health/ready",
    "/api/health",
    "/api/health/live",
    "/api/health/ready",
    "/robots.txt",
    "/sitemap.xml",
    "/favicon.ico",
})


def get_client_ip() -> str:
    """Client IP for limiter buckets (ProxyFix-aware, X-Forwarded-For fallback)."""
    if getattr(request, "access_route", None):
        route = request.access_route
        if route:
            return route[0]
    forwarded = (request.headers.get("X-Forwarded-For") or "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address() or "127.0.0.1"


def is_public_unlimited_request(req: Optional[Request] = None) -> bool:
    """Read-only public assets/pages that must not hit a small global cap."""
    req = req or request
    method = (req.method or "GET").upper()
    if method not in ("GET", "HEAD", "OPTIONS"):
        return False
    path = (req.path or "").lower()
    if path in _PUBLIC_GET_EXACT:
        return True
    if any(path.startswith(prefix) for prefix in _PUBLIC_GET_PREFIXES):
        return True
    if req.endpoint == "static":
        return True
    return False


def should_skip_global_rate_limit() -> bool:
    """Flask-Limiter request_filter hook — skip baseline limits for public reads."""
    return is_public_unlimited_request()


def _retry_after_seconds(exc) -> int:
    retry = getattr(exc, "retry_after", None)
    if retry is not None:
        try:
            return max(1, int(retry))
        except (TypeError, ValueError):
            pass
    get_retry = getattr(exc, "get_retry_after", None)
    if callable(get_retry):
        try:
            value = get_retry()
            if value is not None:
                return max(1, int(value))
        except Exception:
            pass
    return 60


def build_rate_limit_response(exc):
    """JSON for API/AJAX; plain text for HTML forms."""
    retry_after = _retry_after_seconds(exc)
    wants_json = (
        request.path.startswith("/api/")
        or request.path.startswith("/chat/api")
        or request.is_json
        or "application/json" in (request.headers.get("Accept") or "")
    )
    if wants_json:
        resp = jsonify(
            error="rate_limit_exceeded",
            message="Слишком много запросов. Попробуйте позже.",
            retry_after=retry_after,
        )
    else:
        from flask import make_response

        resp = make_response("Слишком много запросов. Попробуйте позже.", 429)
    resp.headers["Retry-After"] = str(retry_after)
    return resp, 429


def apply_proxy_fix(app) -> None:
    """Trust X-Forwarded-* from Nginx when enabled in config."""
    if not app.config.get("RATELIMIT_TRUST_PROXY", True):
        return
    try:
        from werkzeug.middleware.proxy_fix import ProxyFix
    except ImportError:
        app.logger.warning("ProxyFix unavailable — client IP may be incorrect behind Nginx")
        return
    x_for = int(app.config.get("RATELIMIT_PROXY_X_FOR", 1) or 1)
    x_proto = int(app.config.get("RATELIMIT_PROXY_X_PROTO", 1) or 1)
    x_host = int(app.config.get("RATELIMIT_PROXY_X_HOST", 1) or 1)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=x_for, x_proto=x_proto, x_host=x_host)


def limit_by_config(limiter, limit_value: str, *, methods: Optional[Iterable[str]] = None):
    """Apply endpoint limit using canonical client IP key."""
    if limiter is None:
        def _noop(f: F) -> F:
            return f
        return _noop

    def _decorator(f: F) -> F:
        kwargs = {"key_func": get_client_ip}
        if methods:
            kwargs["methods"] = list(methods)
        return limiter.limit(limit_value, **kwargs)(f)

    return _decorator
