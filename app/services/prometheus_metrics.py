"""
Prometheus metrics for Safari bookings system.

Provides metrics for monitoring booking system health and performance.
"""
from prometheus_client import Counter, Histogram, Gauge, Info
import logging
import time as _time

logger = logging.getLogger(__name__)

# Counters
booking_created = Counter(
    'safari_bookings_created_total',
    'Total number of bookings created',
    ['status']
)

booking_status_changed = Counter(
    'safari_bookings_status_changed_total',
    'Total number of booking status changes',
    ['from_status', 'to_status']
)

api_requests = Counter(
    'safari_api_requests_total',
    'Total number of API requests',
    ['endpoint', 'method', 'status_code']
)

email_sent = Counter(
    'safari_emails_sent_total',
    'Total number of emails sent',
    ['email_type']
)

cache_hits = Counter(
    'safari_cache_hits_total',
    'Total number of cache hits'
)

cache_misses = Counter(
    'safari_cache_misses_total',
    'Total number of cache misses'
)

# Histograms
booking_creation_time = Histogram(
    'safari_booking_creation_seconds',
    'Time to create a booking',
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0)
)

api_response_time = Histogram(
    'safari_api_response_seconds',
    'API response time',
    ['endpoint', 'method'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0)
)

# Gauges
active_bookings = Gauge(
    'safari_active_bookings',
    'Number of active (pending or confirmed) bookings'
)

total_participants = Gauge(
    'safari_total_participants',
    'Total number of unique participants'
)

system_health = Gauge(
    'safari_system_health',
    'System health status (1=healthy, 0=unhealthy)'
)

# Общий слой (MyWave)
_uptime = Gauge(
    "mywave_uptime_seconds",
    "Seconds since this process started (best-effort monotonic base)",
)
_process_start = _time.monotonic()
mywave_build = Info("mywave_build", "Build / deploy metadata (from env or config)")
_build_info_set = False


def update_metrics():
    """Update all metrics from database."""
    global _build_info_set
    try:
        from app.database.models import SafariBooking, Participant
        from flask import current_app

        _uptime.set(_time.monotonic() - _process_start)

        with current_app.app_context():
            if not _build_info_set:
                try:
                    mywave_build.info(
                        {"version": str(current_app.config.get("VERSION", "unknown"))}
                    )
                except (ValueError, TypeError):
                    pass
                _build_info_set = True
            # Update active bookings
            active_count = SafariBooking.query.filter(
                SafariBooking.status.in_(['pending', 'confirmed'])
            ).count()
            active_bookings.set(active_count)
            
            # Update total participants
            participant_count = Participant.query.count()
            total_participants.set(participant_count)
            
            # System is healthy if we can reach the database
            system_health.set(1)
            
            logger.debug(f"Metrics updated: active_bookings={active_count}, participants={participant_count}")
            return True
    except Exception as e:
        logger.error(f"Failed to update metrics: {str(e)}")
        system_health.set(0)
        return False


def record_booking_created(booking_status: str = 'pending'):
    """Record a booking creation event."""
    booking_created.labels(status=booking_status).inc()


def record_status_change(from_status: str, to_status: str):
    """Record a booking status change."""
    booking_status_changed.labels(from_status=from_status, to_status=to_status).inc()


def record_api_request(endpoint: str, method: str, status_code: int):
    """Record an API request."""
    api_requests.labels(endpoint=endpoint, method=method, status_code=status_code).inc()


def record_email(email_type: str):
    """Record an email sent."""
    email_sent.labels(email_type=email_type).inc()


def record_cache_hit():
    """Record a cache hit."""
    cache_hits.inc()


def record_cache_miss():
    """Record a cache miss."""
    cache_misses.inc()
