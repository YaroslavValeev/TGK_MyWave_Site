# app/services/ai_router.py
import os
from datetime import datetime
from flask import current_app
import logging
from openai import OpenAI
from app.services.google_sheets_service import get_sheet_data, append_to_sheet, get_history_by_client_id, save_message
# from app.services.responses_api import get_response_from_assistant  # Удалено из глобального импорта

logger = logging.getLogger(__name__)

# Создание клиента OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_user_chat_history(client_id):
    """
    Получает историю диалога пользователя из Google Sheets.
    
    Args:
        client_id (str): Идентификатор клиента
        
    Returns:
        list: Список сообщений в формате для GPT
    """
    try:
        # Проверяем наличие необходимых конфигураций
        required_configs = ["GOOGLE_SERVICE_ACCOUNT_FILE", "SPREADSHEET_ID", "GOOGLE_WORKSHEET_NAME"]
        missing_configs = [config for config in required_configs if not current_app.config.get(config)]
        if missing_configs:
            logger.error(f"Отсутствуют необходимые конфигурации: {missing_configs}")
            return []
            
        records = get_sheet_data(
            current_app.config["GOOGLE_SERVICE_ACCOUNT_FILE"],
            current_app.config["SPREADSHEET_ID"],
            current_app.config["GOOGLE_WORKSHEET_NAME"]
        )
        
        if not records:
            logger.warning("Таблица пуста")
            return []
            
        # Проверяем наличие необходимых колонок
        required_columns = ["client_id", "datetime", "message"]
        if not all(col in records[0] for col in required_columns):
            logger.error(f"Отсутствуют необходимые колонки. Требуются: {required_columns}")
            return []
            
        history = [r for r in records if str(r.get("client_id")) == str(client_id)]
        history.sort(key=lambda x: x.get("datetime", ""))
        return [{"role": "user", "content": h["message"]} for h in history]
    except Exception as e:
        logger.error(f"Ошибка получения истории: {str(e)}")
        return []

def save_chat_message(client_id, message, reply):
    """
    Сохраняет сообщение пользователя и ответ в Google Sheets.
    
    Args:
        client_id (str): Идентификатор клиента
        message (str): Сообщение пользователя
        reply (str): Ответ системы
    """
    try:
        if not all([client_id, message, reply]):
            logger.error("Не все необходимые данные предоставлены")
            return
            
        # Проверяем наличие необходимых конфигураций
        required_configs = ["GOOGLE_SERVICE_ACCOUNT_FILE", "SPREADSHEET_ID", "GOOGLE_WORKSHEET_NAME"]
        missing_configs = [config for config in required_configs if not current_app.config.get(config)]
        if missing_configs:
            logger.error(f"Отсутствуют необходимые конфигурации: {missing_configs}")
            return
            
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row_data = [client_id, current_time, message, reply]
        
        append_to_sheet(
            current_app.config["GOOGLE_SERVICE_ACCOUNT_FILE"],
            current_app.config["SPREADSHEET_ID"],
            current_app.config["GOOGLE_WORKSHEET_NAME"],
            row_data
        )
        logger.info(f"Сообщение успешно сохранено для клиента {client_id}")
    except Exception as e:
        logger.error(f"Ошибка сохранения сообщения: {str(e)}")

def smart_gpt_response(message, client_id="anonymous", source="web"):
    # Получаем историю чата пользователя
    chat_history = get_history_by_client_id(client_id)

    # Импортируем get_response_from_assistant только внутри функции, чтобы избежать циклического импорта
    from app.services.responses_api import get_response_from_assistant
    reply = get_response_from_assistant(message, chat_history=chat_history)

    save_message(client_id, message)
    save_message(client_id, reply)

    return reply
