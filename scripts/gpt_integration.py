import openai
import os
from dotenv import load_dotenv

# Загружаем API ключ из .env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  
GPT_ID = os.getenv("GPTS_MODEL", "gpt-4o")  # ID GPT по умолчанию

# Проверяем, что ключ API был найден
if not OPENAI_API_KEY:
    raise ValueError("API ключ OpenAI не найден в переменных окружения.")

openai.api_key = OPENAI_API_KEY

def ask_gpt(prompt, chat_history=None):
    """
    Функция для отправки запроса в GPT модель.
    
    :param prompt: Строка, содержащая запрос пользователя.
    :param chat_history: История чата (по желанию), передается как список сообщений.
    
    :return: Ответ от модели или сообщение об ошибке.
    """
    messages = [{"role": "system", "content": "Ты умный помощник, отвечай понятно и по делу."}]
    
    # Добавляем историю чата, если она предоставлена
    if chat_history:
        messages += chat_history
    
    # Добавляем текущее сообщение пользователя
    messages.append({"role": "user", "content": prompt})

    try:
        # Отправляем запрос в модель
        response = openai.ChatCompletion.create(
            model=GPT_ID,
            messages=messages,
            max_tokens=150,
            temperature=0.7
        )
        # Возвращаем ответ
        return response.choices[0].message["content"]
    
    except openai.error.OpenAIError as e:
        # Если произошла ошибка с OpenAI API
        return f"Ошибка GPT: {e.user_message or str(e)}"
    
    except Exception as e:
        # Для всех остальных ошибок
        return f"Неизвестная ошибка: {str(e)}"
