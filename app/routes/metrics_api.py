"""
Prometheus metrics export API endpoint.

Provides /metrics endpoint for Prometheus scraping.
"""

from flask import Blueprint, current_app
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import logging

logger = logging.getLogger(__name__)

metrics_bp = Blueprint("metrics", __name__, url_prefix="/metrics")


@metrics_bp.route("", methods=["GET"])
def prometheus_metrics():
    """Export metrics in Prometheus format."""
    try:
        from app.services.prometheus_metrics import update_metrics

        # Update metrics before export
        update_metrics()

        # Generate Prometheus metrics output
        metrics_output = generate_latest()

        return metrics_output, 200, {"Content-Type": CONTENT_TYPE_LATEST}
    except Exception as e:
        logger.error(f"Failed to export metrics: {str(e)}")
        return {"error": "Failed to generate metrics"}, 500


@metrics_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for monitoring."""
    try:
        from app.database.models import db
        from sqlalchemy import text

        # Test database connection
        db.session.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }, 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }, 503
