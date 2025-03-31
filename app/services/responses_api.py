import openai
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Получаем API ключ и ID ассистента
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

# Устанавливаем API ключ
openai.api_key = OPENAI_API_KEY

def get_response_from_assistant(prompt):
    """
    Получает ответ от ассистента OpenAI.
    
    Args:
        prompt (str): Текст запроса к ассистенту
        
    Returns:
        str: Ответ от ассистента
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Ошибка при получении ответа: {str(e)}"
