# Monitoring & Alerting

This document contains recommended steps and example alert rules to monitor the MyWave application.

## What we added

- `/api/health` — returns structured checks for `database`, `cache`, and optional `ai_gateway` (enable with `ENABLE_AI_HEALTH_CHECK=1`).
- Optional Sentry integration: provide `SENTRY_DSN` to forward unhandled exceptions.
- Telegram alert helper: `app.services.monitoring.send_monitoring_alert(message)` — useful for critical alerts.

## Redis-backed rate limiter (optional)

The AI gateway can use a Redis-backed sliding-window rate limiter for cross-process
rate limiting. This is useful when running multiple web workers or instances.

How to enable

1. Ensure `redis` Python package is installed (it's already present in
   `requirements.txt` for SocketIO; if not, run `pip install redis`).
2. Set the following environment variables (example in `.env.sample`):

```text
AI_GATEWAY_RATE_LIMIT_BACKEND=redis
REDIS_URL=redis://localhost:6379/0
AI_GATEWAY_RATE_LIMIT_COUNT=60
AI_GATEWAY_RATE_LIMIT_WINDOW=60
```

3. Restart the application. When configured, the app will attempt to initialize a
   `RedisRateLimiter` (safe fallback to the in-memory limiter is in place if
   Redis is unavailable or initialization fails).

Notes and recommendations

- The implementation uses a small Lua script and Redis sorted sets to perform
  atomic sliding-window checks. This keeps per-bucket state for the window in a
  compact form.
- On transient Redis errors the limiter logs a warning and falls back to
  allowing requests (fail-open). If you prefer strict enforcement, we can
  change behavior to fail-closed instead.
- Recommended Redis settings: use a small dedicated DB (e.g., `redis://host:6379/1`),
  enable connection pooling and proper auth. Monitor Redis memory and evictions
  if you have many distinct API keys or IP buckets.

Testing

- Unit tests were added in `tests/unit/test_redis_rate_limiter.py` that mock the
  redis client and verify both fallback and Redis-path behavior.


## Example Prometheus Alert (Alertmanager)

Save example rule to `monitoring/alert_rules.yml` and configure Prometheus to load it.

```text
groups:
  - name: mywave-alerts
    rules:
      - alert: MyWaveHighErrorRate
        expr: increase(flask_http_request_errors_total[5m]) > 5
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate on MyWave"
          description: "{{ $labels.instance }} has >5 errors in the last 5m"

      - alert: MyWaveHealthUnhealthy
        expr: up{job="mywave"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "MyWave instance down"
          description: "Instance {{ $labels.instance }} is down according to up metric"
```

## Runbook (brief)

1. If Sentry shows an exception with many occurrences, inspect stack trace and recent deploys.
2. If Telegram alert triggers, open Sentry and check /api/health for affected components.
3. For persistent DB failures, check DB connectivity and credentials, and restore from recent backups if needed.
