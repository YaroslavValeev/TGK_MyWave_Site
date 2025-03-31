import os
from enum import Enum
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

class ChatMode(str, Enum):
    CHAT_API = "chat_api"
    RESPONSES_API = "responses_api"

# Устанавливаем режим по умолчанию через .env
CHAT_MODE = os.getenv("OPENAI_CHAT_MODE", ChatMode.RESPONSES_API)
