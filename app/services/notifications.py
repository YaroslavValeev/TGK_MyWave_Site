import requests
from config import Config
import logging
import time
from functools import wraps
from app.modules.logger import get_logger

logger = get_logger(__name__)

def retry(attempts=3, delay=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(1, attempts+1):
                try:
                    result = func(*args, **kwargs)
                    logger.info(f"Уведомление отправлено (попытка {i})")
                    return result
                except Exception as e:
                    logger.warning(f"Попытка {i} не удалась: {e}", exc_info=True)
                    time.sleep(delay)
            logger.error("Все попытки отправки уведомления неуспешны")
        return wrapper
    return decorator

def send_telegram_notification(name, phone, slot_or_message):
    """
    Отправляет уведомление в Telegram.
    
    Args:
        name: Имя
        phone: Телефон
        slot_or_message: Время слота или произвольное сообщение
    """
    try:
        # Если slot_or_message содержит переносы строк, это полное сообщение
        if '\n' in str(slot_or_message):
            message = str(slot_or_message)
        else:
            # Старый формат для совместимости
            message = (
                f"📌 Новая запись на тренировку!\n\n"
                f"👤 Имя: {name}\n"
                f"📱 Телефон: {phone}\n"
                f"🕒 Время: {slot_or_message}"
            )
        
        if not Config.TELEGRAM_BOT_TOKEN or not Config.TELEGRAM_CHAT_ID:
            logger.warning("Telegram токен или chat_id не настроены")
            return False
        
        response = requests.get(
            f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage",
            params={
                "chat_id": Config.TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML"
            }
        )
        
        if not response.ok:
            logger.error(f"Ошибка отправки в Telegram: {response.text}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления: {str(e)}")
        return False 