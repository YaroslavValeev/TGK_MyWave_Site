import requests
import time
import logging
from functools import wraps
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
