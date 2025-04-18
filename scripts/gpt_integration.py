import openai
import os
from dotenv import load_dotenv
import time
import logging

logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

if not OPENAI_API_KEY or not ASSISTANT_ID:
    raise ValueError("API ключ OpenAI или ID ассистента не найдены в переменных окружения.")

openai.api_key = OPENAI_API_KEY

def ask_gpt(prompt, chat_history=None):
    """
    Функция для отправки запроса ассистенту OpenAI.
    
    :param prompt: Строка, содержащая запрос пользователя.
    :param chat_history: Не используется в этой версии.
    
    :return: Ответ от ассистента или сообщение об ошибке.
    """
    try:
        logger.info(f"Creating new thread for prompt: {prompt[:50]}...")
        
        # Создаем новый тред
        thread = openai.beta.threads.create()

        # Добавляем сообщение в тред
        logger.info("Adding message to thread...")
        openai.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=prompt
        )

        # Запускаем ассистента
        logger.info("Starting assistant...")
        run = openai.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )

        # Ждем завершения с таймаутом
        max_retries = 30  # 30 seconds timeout
        retries = 0
        while retries < max_retries:
            run_status = openai.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            if run_status.status == 'completed':
                break
            time.sleep(1)
            retries += 1
            
        if retries >= max_retries:
            logger.error("Assistant response timeout")
            return "Извините, время ожидания ответа истекло. Попробуйте позже."

        # Получаем сообщения
        messages = openai.beta.threads.messages.list(thread_id=thread.id)
        
        if not messages.data:
            logger.error("No messages received from assistant")
            return "Извините, не удалось получить ответ. Попробуйте позже."
            
        # Возвращаем последнее сообщение ассистента
        return messages.data[0].content[0].text.value

    except Exception as e:
        logger.error(f"Error in ask_gpt: {str(e)}")
        return f"Извините, произошла ошибка при обработке запроса: {str(e)}"
