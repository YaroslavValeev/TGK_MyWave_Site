import requests
import logging
from datetime import datetime
from flask import current_app
from app.services.google_sheets_service import append_to_sheet

logger = logging.getLogger(__name__)

def log_dialog(client_id, source, message, reply):
    """
    Логирует диалог в Google Sheets.
    
    Args:
        client_id (str): Идентификатор клиента
        source (str): Источник сообщения
        message (str): Сообщение пользователя
        reply (str): Ответ системы
        
    Raises:
        ValueError: Если не все параметры предоставлены
        Exception: При ошибках записи в таблицу
    """
    try:
        if not all([client_id, source, message, reply]):
            raise ValueError("Не все необходимые параметры предоставлены")
            
        values = [[client_id, source, message, reply, datetime.now().isoformat()]]
        
        # Проверяем наличие необходимых конфигураций
        if not current_app.config.get("SPREADSHEET_ID"):
            raise ValueError("SPREADSHEET_ID не настроен")
            
        # Записываем данные в таблицу
        append_to_sheet(
            current_app.config["GOOGLE_SERVICE_ACCOUNT_FILE"],
            current_app.config["SPREADSHEET_ID"],
            current_app.config["GOOGLE_WORKSHEET_NAME"],
            values[0]
        )
        
        logger.info(f"Диалог успешно записан для клиента {client_id}")
        
    except Exception as e:
        logger.error(f"Ошибка записи диалога: {str(e)}")
        # Не пробрасываем ошибку дальше, чтобы не прерывать основной поток

def notify_admin(error_message):
    try:
        message = f"🚨 Server Error:\n{error_message}"
        requests.post(
            f"https://api.telegram.org/bot{current_app.config['TELEGRAM_BOT_TOKEN']}/sendMessage",
            json={"chat_id": current_app.config["ADMIN_CHAT_ID"], "text": message}
        )
    except Exception as e:
        logger.error(f"Admin notification failed: {str(e)}")

def process_chat_message(message):
    """
    Обрабатывает входящее сообщение чата и возвращает ответ.
    """
    try:
        # Простая заглушка для демонстрации
        response = f"Получено сообщение: {message}"
        return response
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        return "Извините, произошла ошибка при обработке сообщения."