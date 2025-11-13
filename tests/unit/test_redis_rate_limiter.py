import types
import time

from app.ai import security


def test_get_limiter_falls_back_to_inmemory(monkeypatch, app):
    """If backend='redis' but redis package is not available, get_limiter()
    should fall back to the in-memory SimpleRateLimiter."""
    # Ensure module-level state is reset for test isolation
    if hasattr(security, '_limiter'):
        monkeypatch.setattr(security, '_limiter', None)

    monkeypatch.setitem(app.config, 'AI_GATEWAY_RATE_LIMIT_BACKEND', 'redis')
    monkeypatch.setitem(app.config, 'AI_GATEWAY_REDIS_URL', 'redis://localhost:6379/0')
    # Simulate redis package missing
    monkeypatch.setattr(security, '_redis_available', False)

    with app.app_context():
        limiter = security.get_limiter()
        assert isinstance(limiter, security.SimpleRateLimiter)


def test_redis_rate_limiter_used_and_script_called(monkeypatch, app):
    """When redis is available and backend='redis', get_limiter() should
    return a RedisRateLimiter which uses the registered Lua script to make
    atomic allow decisions.

    We'll provide a fake redis client where register_script returns a callable
    that simulates allowing requests until a limit is reached.
    """
    # Reset
    if hasattr(security, '_limiter'):
        monkeypatch.setattr(security, '_limiter', None)

    monkeypatch.setitem(app.config, 'AI_GATEWAY_RATE_LIMIT_BACKEND', 'redis')
    monkeypatch.setitem(app.config, 'AI_GATEWAY_REDIS_URL', 'redis://fake/0')
    monkeypatch.setitem(app.config, 'AI_GATEWAY_RATE_LIMIT_COUNT', 2)
    monkeypatch.setitem(app.config, 'AI_GATEWAY_RATE_LIMIT_WINDOW', 60)

    # Build a fake redis module and client
    fake_redis_mod = types.SimpleNamespace()

    class FakeClient:
        def __init__(self):
            self.registered = None

        def register_script(self, script):
            # script -> return a callable that will be used as the Lua script
            def callable_script(keys=None, args=None):
                # keys argument is used to separate buckets (we expect ai_rl:<bucket>)
                key = keys[0] if keys else 'unknown'
                if not hasattr(self, '_calls_per_key'):
                    self._calls_per_key = {}
                cnt = self._calls_per_key.get(key, 0) + 1
                self._calls_per_key[key] = cnt
                # Simulate allow for first 2 calls per key, then deny
                if cnt <= 2:
                    return 1
                return 0

            return callable_script

    def from_url(url):
        return FakeClient()

    fake_redis_mod.Redis = types.SimpleNamespace(from_url=from_url)

    # Patch the security module to see redis as available and provide our fake module
    monkeypatch.setattr(security, 'redis', fake_redis_mod)
    monkeypatch.setattr(security, '_redis_available', True)

    with app.app_context():
        limiter = security.get_limiter()
        # We expect a RedisRateLimiter instance
        assert type(limiter).__name__ == 'RedisRateLimiter'

        # Use the limiter to allow twice, then block on the third
        bucket = 'test-bucket'
        assert limiter.allow(bucket) is True
        assert limiter.allow(bucket) is True
        assert limiter.allow(bucket) is False

        # calling for a different bucket should be allowed again
        assert limiter.allow('other-bucket') is True
