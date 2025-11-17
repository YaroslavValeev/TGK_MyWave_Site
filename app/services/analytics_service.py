"""
Analytics and event logging service for Safari bookings.

Logs booking events to Google Sheets and tracks system metrics.
"""
from typing import Dict, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def log_booking_event(booking_data: Dict[str, Any], event_type: str = 'created') -> bool:
    """Log a booking event to analytics.
    
    Args:
        booking_data: Dictionary with booking details (id, participant_id, status, etc.)
        event_type: Type of event ('created', 'confirmed', 'cancelled', 'completed')
    
    Returns:
        True if logging succeeded, False otherwise
    """
    try:
        from app.services.google_sheets_service import append_record
        from flask import current_app
        
        sheet_id = current_app.config.get('ANALYTICS_SHEET_SPREADSHEET_ID')
        sheet_name = 'safari_bookings'
        
        if not sheet_id:
            logger.warning('ANALYTICS_SHEET_SPREADSHEET_ID not configured; skipping sheet write')
            return False
        
        # Build analytics row
        timestamp = datetime.utcnow().isoformat()
        row = [
            timestamp,
            event_type,
            str(booking_data.get('id', '')),
            str(booking_data.get('participant_id', '')),
            booking_data.get('status', ''),
            str(booking_data.get('start_date', '')),
            str(booking_data.get('days', '')),
            booking_data.get('message', '')[:100] if booking_data.get('message') else '',
        ]
        
        append_record(sheet_id, sheet_name, row)
        logger.info(f"Booking event logged: {event_type} (booking_id={booking_data.get('id')})")
        return True
        
    except Exception as e:
        logger.error(f"Failed to log booking event: {str(e)}")
        return False


def get_booking_stats() -> Dict[str, Any]:
    """Get booking statistics from database.
    
    Returns:
        Dictionary with stats: total_bookings, by_status, by_date_range
    """
    try:
        from app.database.models import SafariBooking
        from sqlalchemy import func
        from flask import current_app
        
        with current_app.app_context():
            total = SafariBooking.query.count()
            
            # Group by status
            status_counts = {}
            for status in ['pending', 'confirmed', 'cancelled', 'completed']:
                count = SafariBooking.query.filter_by(status=status).count()
                if count > 0:
                    status_counts[status] = count
            
            return {
                'total_bookings': total,
                'by_status': status_counts,
                'timestamp': datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.error(f"Failed to get booking stats: {str(e)}")
        return {
            'total_bookings': 0,
            'by_status': {},
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }


def log_api_call(endpoint: str, method: str, status_code: int, 
                 response_time_ms: float, user_id: Optional[int] = None) -> bool:
    """Log API call metrics.
    
    Args:
        endpoint: API endpoint path (e.g., /api/safari/bookings)
        method: HTTP method (GET, POST, etc.)
        status_code: HTTP response status code
        response_time_ms: Response time in milliseconds
        user_id: Optional user ID for tracking
    
    Returns:
        True if logging succeeded, False otherwise
    """
    try:
        from app.services.google_sheets_service import append_record
        from flask import current_app
        
        sheet_id = current_app.config.get('ANALYTICS_SHEET_SPREADSHEET_ID')
        sheet_name = 'api_calls'
        
        if not sheet_id:
            logger.debug('ANALYTICS_SHEET_SPREADSHEET_ID not configured; skipping API metrics write')
            return False
        
        timestamp = datetime.utcnow().isoformat()
        row = [
            timestamp,
            endpoint,
            method,
            str(status_code),
            f"{response_time_ms:.2f}ms",
            str(user_id) if user_id else 'anonymous',
        ]
        
        append_record(sheet_id, sheet_name, row)
        return True
        
    except Exception as e:
        logger.debug(f"Failed to log API call: {str(e)}")
        return False


class AnalyticsMiddleware:
    """Middleware for tracking API calls and performance metrics."""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize middleware with Flask app."""
        self.app = app
        app.before_request(self.before_request)
        app.after_request(self.after_request)
    
    def before_request(self):
        """Record request start time."""
        from flask import g
        import time
        g.start_time = time.time()
    
    def after_request(self, response):
        """Log API call after request completes."""
        from flask import g, request
        import time
        
        try:
            if hasattr(g, 'start_time'):
                elapsed_ms = (time.time() - g.start_time) * 1000
                
                # Only log Safari API endpoints
                if '/api/safari' in request.path:
                    user_id = None
                    try:
                        from flask_login import current_user
                        if current_user.is_authenticated:
                            user_id = current_user.id
                    except Exception:
                        pass
                    
                    log_api_call(
                        endpoint=request.path,
                        method=request.method,
                        status_code=response.status_code,
                        response_time_ms=elapsed_ms,
                        user_id=user_id
                    )
        except Exception as e:
            logger.debug(f"Analytics middleware error: {str(e)}")
        
        return response
