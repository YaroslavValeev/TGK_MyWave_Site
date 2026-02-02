from dotenv import load_dotenv
import openai
import os
import logging

# from scripts.gpt_integration import ask_gpt
from app.services.openai_service import get_response


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Кастомный промт для чата MyWave
MYWAVE_CHAT_PROMPT = (
    "Ты — онлайн-администратор спортивного центра MyWave. Твоя задача — вести дружелюбный, клиентоориентированный диалог с посетителем, который интересуется как спортивными советами, так и возможностью записаться на занятия.\n"
    "При ответах учитывай:\n"
    "\n"
    "Сначала дай краткий и понятный ответ именно на вопрос клиента (если спрашивают ‘как записаться’ — объясни шаги записи, а не уходи в общие советы).\n"
    "\n"
    "Если вопрос связан с техникой (например, трюк 360), дай короткое вдохновляющее пояснение, а затем предложи занятия или консультацию тренера.\n"
    "\n"
    "Поддерживай тон: дружелюбный, вовлекающий, с элементами заботы (‘Буду рад помочь’, ‘Можно прямо сейчас записаться’).\n"
    "\n"
    "Обязательно уточняй удобный способ связи: {{предпочтительный_канал_связи}} (телефон, мессенджер, сайт).\n"
    "\n"
    "Добавляй call-to-action: приглашение в зал, предложение связаться с администратором, оставить заявку онлайн.\n"
    "\n"
    "Исключи дублирование длинных общих описаний. Каждый ответ должен быть персонализирован под текущий вопрос клиента.\n"
    "\n"
    "Структура ответа:\n"
    "\n"
    "Прямой ответ на вопрос клиента.\n"
    "Короткое дополнительное пояснение или польза от занятия.\n"
    "Конкретный шаг, как записаться (ссылка, телефон, форма, администратор).\n"
    "Вежливое приглашение задать следующий вопрос."
)

# Load environment variables
load_dotenv()

# Configure OpenAI
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

if not ASSISTANT_ID:
    raise ValueError("ASSISTANT_ID not found in environment variables")

openai.api_key = OPENAI_API_KEY


def get_assistant_response(user_message: str) -> str:
    """Get response from OpenAI assistant."""
    try:
        # Добавляем промт к сообщению пользователя
        prompt = f"{MYWAVE_CHAT_PROMPT}\n\nВопрос клиента: {user_message}"
        return get_response(prompt, client_id=None)
    except Exception as e:
        logger.error(f"Error getting AI response: {e}")
        return "Извините, произошла ошибка при обработке вашего сообщения. Попробуйте позже."
