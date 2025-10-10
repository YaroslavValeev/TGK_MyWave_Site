import requests
import logging
from datetime import datetime
from flask import current_app

logger = logging.getLogger(__name__)

def notify_admin(error_message):
    try:
        message = f"🚨 Server Error:\n{error_message}"
        requests.post(
            f"https://api.telegram.org/bot{current_app.config['TELEGRAM_BOT_TOKEN']}/sendMessage",
            json={"chat_id": current_app.config["ADMIN_CHAT_ID"], "text": message}
        )
    except Exception as e:
        logger.error(f"Admin notification failed: {str(e)}")