"""
Analytics and event logging service for Safari bookings.

Logs booking events to Google Sheets and tracks system metrics.
"""
from typing import Dict, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def log_booking_event(booking_data: Dict[str, Any], event_type: str = 'created') -> bool:
    """
    Логирование событий бронирования Safari через единый аналитический слой
    (google_sheets_analytics.log_analytics_event) в лист safari_bookings.
    """
    try:
        from flask import current_app, request
        from app.services.google_sheets_analytics import log_analytics_event

        # Выбираем таблицу для аналитики:
        # 1) Отдельная ANALYTICS_SHEET_SPREADSHEET_ID, если задана
        # 2) Иначе основной SPREADSHEET_ID
        sheet_id = current_app.config.get('ANALYTICS_SHEET_SPREADSHEET_ID') \
                   or current_app.config.get('SPREADSHEET_ID')

        if not sheet_id:
            logger.warning('log_booking_event: no analytics spreadsheet configured; skipping')
            return False

        # Метаданные бронирования — сохраняем всё в meta (JSON)
        meta = {
            'booking_id': booking_data.get('id'),
            'participant_id': booking_data.get('participant_id'),
            'status': booking_data.get('status'),
            'start_date': str(booking_data.get('start_date', '')),
            'days': booking_data.get('days'),
            'route_id': booking_data.get('route_id'),
            'message': booking_data.get('message'),
        }

        # Пытаемся снять IP и User-Agent (если есть контекст запроса)
        try:
            ip = request.remote_addr or ''
            ua = request.headers.get('User-Agent', '')
        except Exception:
            ip = ''
            ua = ''

        payload = {
            'event': f'safari_booking_{event_type}',
            'context': 'safari_booking',
            'user_key': str(booking_data.get('participant_id') or ''),
            'item_id': str(booking_data.get('id') or ''),
            'type': 'booking',
            'meta': meta,
            'ip': ip,
            'user_agent': ua,
        }

        ok = log_analytics_event(
            payload,
            spreadsheet_id=sheet_id,
            worksheet_name='safari_bookings'
        )

        if ok:
            logger.info(
                f"Booking event logged via analytics core: {event_type} "
                f"(booking_id={booking_data.get('id')})"
            )
        else:
            logger.warning("log_booking_event: log_analytics_event returned False")

        return ok

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
    """
    Логирование метрик API-вызовов Safari через единый analytics-слой
    в лист api_calls.
    """
    try:
        from flask import current_app, request
        from app.services.google_sheets_analytics import log_analytics_event

        sheet_id = current_app.config.get('ANALYTICS_SHEET_SPREADSHEET_ID') \
                   or current_app.config.get('SPREADSHEET_ID')

        if not sheet_id:
            logger.debug('log_api_call: no analytics spreadsheet configured; skipping API metrics write')
            return False

        try:
            ip = request.remote_addr or ''
            ua = request.headers.get('User-Agent', '')
        except Exception:
            ip = ''
            ua = ''

        payload = {
            'event': 'safari_api_call',
            'context': endpoint,
            'user_key': str(user_id or ''),
            'type': 'api',
            'meta': {
                'method': method,
                'status_code': status_code,
                'response_time_ms': response_time_ms,
            },
            'ip': ip,
            'user_agent': ua,
        }

        ok = log_analytics_event(
            payload,
            spreadsheet_id=sheet_id,
            worksheet_name='api_calls'
        )
        if not ok:
            logger.debug('log_api_call: log_analytics_event returned False')
        return ok

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
                
                # Логируем только Safari-бронирования (booking_api blueprint)
                if request.blueprint == 'booking_api' or request.path.startswith('/api/booking'):
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
