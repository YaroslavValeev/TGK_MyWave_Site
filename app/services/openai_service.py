from openai import OpenAI
import os
from dotenv import load_dotenv
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Создание клиента OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

def get_chat_response(user_message: str, chat_history=None, client_id=None, source="web"):
    """
    Получает ответ от GPT с учетом истории диалога.
    
    Args:
        user_message (str): Сообщение пользователя
        chat_history (list, optional): История диалога
        client_id (str, optional): Идентификатор клиента
        source (str, optional): Источник запроса
        
    Returns:
        str: Ответ от GPT
        
    Raises:
        ValueError: Если сообщение пустое
        Exception: При ошибках работы с API
    """
    try:
        if not user_message:
            raise ValueError("Сообщение не может быть пустым")
            
        if not OPENAI_API_KEY:
            raise ValueError("API ключ OpenAI не настроен")
        
        # Формируем сообщения для GPT
        messages = []
        if chat_history:
            messages.extend(chat_history)
        messages.append({"role": "user", "content": user_message})
        
        # Получаем ответ от GPT используя новый клиент
        response = client.chat.completions.create(
            model="gpt-4",  # Используем базовую модель
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        if not response or not response.choices:
            raise ValueError("Не удалось получить ответ от GPT")
            
        reply = response.choices[0].message.content
        logger.info(f"Успешно получен ответ от GPT для клиента {client_id}")
        return reply
        
    except Exception as e:
        logger.error(f"Ошибка при получении ответа от GPT: {str(e)}")
        return f"Извините, произошла ошибка при обработке вашего запроса: {str(e)}"