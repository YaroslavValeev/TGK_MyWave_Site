import time
import threading
from collections import deque
from functools import wraps
from typing import Optional

from flask import request, current_app, g, jsonify, abort
from app.ai.metrics import AUTH_FAILURE_COUNTER, RATE_LIMIT_COUNTER
import logging


# Try to import redis client; if not available we'll gracefully fall back
try:
    import redis

    _redis_available = True
except Exception:  # ImportError or others
    redis = None
    _redis_available = False


class SimpleRateLimiter:
    """Very small in-memory sliding-window rate limiter.

    This is process-local and intended as a lightweight protection. For
    production a shared store (Redis) + robust limiter should be used.
    """

    def __init__(self, count: int = 60, window_seconds: int = 60):
        self.count = int(count)
        self.window = int(window_seconds)
        self.store = {}  # key -> deque[timestamp]
        self.lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.time()
        with self.lock:
            dq = self.store.get(key)
            if dq is None:
                dq = deque()
                self.store[key] = dq
            # purge old
            cutoff = now - self.window
            while dq and dq[0] < cutoff:
                dq.popleft()
            if len(dq) < self.count:
                dq.append(now)
                return True
            return False


class RedisRateLimiter:
    """Redis-backed sliding window rate limiter using a Lua script for atomicity.

    Uses a sorted set per bucket key and stores timestamps (ms). The Lua script
    removes old entries, checks the current count and adds a new entry if under
    the limit. This class is optional — if the `redis` package or REDIS_URL is
    not configured, the system will fall back to the in-memory limiter.
    """

    LUA_SCRIPT = """
    local key = KEYS[1]
    local now = tonumber(ARGV[1])
    local window_ms = tonumber(ARGV[2])
    local limit = tonumber(ARGV[3])
    local member = ARGV[4]
    -- remove old
    redis.call('ZREMRANGEBYSCORE', key, 0, now - window_ms)
    local cnt = redis.call('ZCARD', key)
    if cnt < limit then
        redis.call('ZADD', key, now, member)
        redis.call('PEXPIRE', key, window_ms + 1000)
        return 1
    end
    return 0
    """

    def __init__(self, redis_url: str, count: int = 60, window_seconds: int = 60):
        if not _redis_available:
            raise RuntimeError("redis package not available")
        self.count = int(count)
        self.window_ms = int(window_seconds) * 1000
        self.client = redis.Redis.from_url(redis_url)
        # register script
        self._script = self.client.register_script(self.LUA_SCRIPT)

    def allow(self, key: str) -> bool:
        try:
            now_ms = int(time.time() * 1000)
            member = f"{now_ms}-{time.time_ns()}"
            res = self._script(
                keys=[f"ai_rl:{key}"], args=[now_ms, self.window_ms, self.count, member]
            )
            return bool(int(res))
        except Exception as e:
            # On redis errors, log and conservatively allow (or deny?) — choose allow to avoid blocking
            logging.getLogger(__name__).warning(
                "Redis rate limiter error, falling back to allow: %s", e
            )
            return True


# module-level limiter instance (will be created lazily)
_limiter: Optional[SimpleRateLimiter] = None


def get_limiter() -> SimpleRateLimiter:
    global _limiter
    if _limiter is None:
        cnt = current_app.config.get("AI_GATEWAY_RATE_LIMIT_COUNT", 60)
        wnd = current_app.config.get("AI_GATEWAY_RATE_LIMIT_WINDOW", 60)
        backend = current_app.config.get("AI_GATEWAY_RATE_LIMIT_BACKEND", "").lower()
        redis_url = current_app.config.get("REDIS_URL") or current_app.config.get(
            "AI_GATEWAY_REDIS_URL"
        )

        if backend == "redis" and redis_url and _redis_available:
            try:
                _limiter = RedisRateLimiter(redis_url, count=cnt, window_seconds=wnd)
                current_app.logger.info(
                    "Using RedisRateLimiter for AI gateway rate limiting"
                )
            except Exception as e:
                current_app.logger.exception(
                    "Failed to initialize RedisRateLimiter, falling back to in-memory: %s",
                    e,
                )
                _limiter = SimpleRateLimiter(count=cnt, window_seconds=wnd)
        else:
            if backend == "redis" and not _redis_available:
                current_app.logger.warning(
                    "Redis backend requested but redis package not available; using in-memory limiter"
                )
            _limiter = SimpleRateLimiter(count=cnt, window_seconds=wnd)
    return _limiter


def _get_api_key_from_request() -> Optional[str]:
    # Prefer Authorization: Bearer <token>
    auth = request.headers.get("Authorization")
    if auth:
        parts = auth.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
    # fallback to X-API-Key header
    key = request.headers.get("X-API-Key") or request.args.get("api_key")
    return key


def require_ai_api_key(view_func=None, *, rate_limit: bool = True):
    """Decorator to enforce API key and optional rate limiting on AI endpoints.

    It respects the following Flask config values:
    - AI_GATEWAY_REQUIRE_API_KEY (bool)
    - AI_GATEWAY_API_KEYS (list)
    - AI_GATEWAY_ENABLE_RATE_LIMIT (bool)
    - AI_GATEWAY_RATE_LIMIT_COUNT, AI_GATEWAY_RATE_LIMIT_WINDOW
    """

    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            require = current_app.config.get("AI_GATEWAY_REQUIRE_API_KEY", False)
            allowed_keys = current_app.config.get("AI_GATEWAY_API_KEYS", []) or []

            api_key = _get_api_key_from_request()

            # If API key is required but none provided -> 401
            if require:
                if not api_key:
                    AUTH_FAILURE_COUNTER.inc()
                    return jsonify({"error": "API key required"}), 401
                if allowed_keys and api_key not in allowed_keys:
                    AUTH_FAILURE_COUNTER.inc()
                    return jsonify({"error": "Invalid API key"}), 401

            # Attach api_key to flask.g for downstream handlers
            g.ai_api_key = api_key

            # Rate limiting
            enable_rl = (
                current_app.config.get("AI_GATEWAY_ENABLE_RATE_LIMIT", False)
                and rate_limit
            )
            if enable_rl:
                limiter = get_limiter()
                # Use the provided api_key as the rate-limiting bucket; if missing, fallback to remote_addr
                bucket = api_key or request.remote_addr or "anon"
                allowed = limiter.allow(bucket)
                if not allowed:
                    RATE_LIMIT_COUNTER.inc()
                    return jsonify({"error": "rate_limit_exceeded"}), 429

            return fn(*args, **kwargs)

        return wrapped

    # support usage as @require_ai_api_key or @require_ai_api_key()
    if view_func:
        return decorator(view_func)
    return decorator
