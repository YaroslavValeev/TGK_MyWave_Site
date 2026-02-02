import os
from enum import Enum
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


class ChatMode(Enum):
    STANDARD = "standard"  # Обычный диалоговый режим (по умолчанию)
    CHAT = "chat"  # Продвинутый чат-режим (например, с историей)
    SUMMARY = "summary"  # Режим кратких резюме/выжимок
    RESPONSES_API = "RESPONSES_API"  # Режим для responses_api
    CHAT_API = "CHAT_API"  # Режим для chat_api


# Устанавливаем режим по умолчанию через .env
CHAT_MODE = os.getenv("OPENAI_CHAT_MODE", ChatMode.STANDARD)

# Mapping режимов к endpoint (пример, для документации)
# endpoint_mode_mapping = {
#     '/ai/message': ChatMode.STANDARD,
#     '/ai/chat': ChatMode.CHAT,
#     '/ai/summary': ChatMode.SUMMARY,
# }
# Можно использовать этот mapping для роутинга или логики выбора режима
