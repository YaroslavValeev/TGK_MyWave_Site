"""Prometheus metrics for the AI Gateway.

Defines Counters and a Histogram. Designed to be safe in tests where
PROMETHEUS_MULTIPROC_DIR may be set.
"""

from prometheus_client import Counter, Histogram, CollectorRegistry, generate_latest
import prometheus_client

# Metric names prefixed with mywave_ai_gateway
REQUEST_COUNTER = Counter(
    "mywave_ai_gateway_requests_total",
    "Total number of requests to the AI gateway",
)

TOOL_CALL_COUNTER = Counter(
    "mywave_ai_gateway_tool_calls_total",
    "Total number of tool calls requested by the model",
)

AUTH_FAILURE_COUNTER = Counter(
    "mywave_ai_gateway_auth_failures_total",
    "Total number of authentication failures for the AI gateway",
)

RATE_LIMIT_COUNTER = Counter(
    "mywave_ai_gateway_rate_limited_total",
    "Total number of rate-limited requests",
)

TOOL_RESULT_COUNTER = Counter(
    "mywave_ai_gateway_tool_results_total",
    "Total number of successful tool results returned",
)

TOOL_VALIDATION_FAILURE_COUNTER = Counter(
    "mywave_ai_gateway_tool_validation_failures_total",
    "Total number of AI tool payload validation failures",
)

CONCIERGE_REQUEST_COUNTER = Counter(
    "mywave_ai_concierge_requests_total",
    "Total number of concierge API requests received",
)

LATENCY_HISTOGRAM = Histogram(
    "mywave_ai_gateway_request_latency_seconds",
    "Latency of AI gateway request handling",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)


def metrics_snapshot() -> bytes:
    """Return the current metrics snapshot as Prometheus exposition bytes."""
    return generate_latest()
