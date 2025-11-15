import requests
import time
import logging
import threading
from functools import wraps
from typing import Optional, Dict, Any
from config import Config
from app.modules.logger import get_logger

logger = get_logger(__name__)


def retry(attempts=3, delay=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Monitoring alert attempt {i} failed: {e}")
                    time.sleep(delay)
            logger.error("All monitoring alert attempts failed")
        return wrapper
    return decorator


@retry(attempts=3, delay=2)
def send_monitoring_alert(message: str, parse_mode: str = 'HTML') -> bool:
    """
    Send a short monitoring alert to configured Telegram chat.
    Returns True if sent, False otherwise.
    This is intentionally minimal: it uses Config.TELEGRAM_BOT_TOKEN and Config.TELEGRAM_CHAT_ID.
    """
    try:
        token = Config.TELEGRAM_BOT_TOKEN
        chat_id = Config.TELEGRAM_CHAT_ID
        if not token or not chat_id:
            logger.warning("Telegram monitoring not configured (missing token or chat_id)")
            return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.get(url, params={"chat_id": chat_id, "text": message, "parse_mode": parse_mode}, timeout=6)
        if not resp.ok:
            logger.error(f"Failed to send monitoring alert: {resp.status_code} {resp.text}")
            return False
        logger.info("Monitoring alert sent to Telegram")
        return True
    except Exception as e:
        logger.exception(f"Exception while sending monitoring alert: {e}")
        raise


def report_exception(exception: Exception, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Report an exception to Sentry (if configured) and trigger a Telegram monitoring alert.
    
    This function is used by the global exception handler in app/__init__.py to centralize
    error reporting. It's defensive and will not raise if monitoring services are missing.
    
    Args:
        exception: The exception that occurred
        context: Optional context dictionary (e.g., {'path': '/api/endpoint', 'method': 'POST'})
    """
    # Log locally
    logger.exception(f'Exception reported: {exception}')

    # Try to capture in Sentry if available
    try:
        import sentry_sdk
        if context:
            with sentry_sdk.push_scope() as scope:
                for key, value in context.items():
                    scope.set_context('request', {key: value})
                sentry_sdk.capture_exception(exception)
        else:
            sentry_sdk.capture_exception(exception)
    except Exception:
        logger.debug('Sentry SDK not available or failed to capture')

    # Trigger a non-blocking Telegram monitoring alert
    try:
        from flask import current_app
        version = current_app.config.get('VERSION', 'unknown')
        path = context.get('path', 'unknown') if context else 'unknown'
        method = context.get('method', 'unknown') if context else 'unknown'
        
        message = f"Unhandled exception in MyWave ({version}): {str(exception)} [{method} {path}]"

        def _alert():
            try:
                send_monitoring_alert(message)
            except Exception:
                logger.debug('Monitoring alert failed')

        threading.Thread(target=_alert, daemon=True).start()
    except Exception:
        logger.debug('Failed to start monitoring alert thread')
