import os
from datetime import timedelta

# Load environment variables from .env as early as possible (local dev).
# Do not override real environment variables (override=False).
try:
    from dotenv import load_dotenv

    load_dotenv(override=False)
except Exception:
    # python-dotenv is optional in some deployments; continue without it.
    pass


def _env_int(name: str, default: int) -> int:
    """Parse int env var safely (never crash on invalid values)."""
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(str(raw).strip())
    except Exception:
        return default

class Config:
    """Основная конфигурация для приложения."""
    SECRET_KEY = os.getenv('SECRET_KEY') or 'hard-to-guess-string'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    GOOGLE_CALENDAR_ID = os.environ.get('GOOGLE_CALENDAR_ID')
    SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
    TIMEZONE = 'Europe/Moscow'
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

    # Настройки для OpenAI и GPT
    GPTS_MODEL = os.getenv("GPTS_MODEL", "gpt-4")
    FINE_TUNED_MODEL = os.getenv("FINE_TUNED_MODEL", "gpt-4")
    FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gpt-3.5-turbo")
    ASSISTANT_ID = os.getenv("ASSISTANT_ID")

    # === MCP / External Tools (optional) ===
    ENABLE_MCP = os.getenv("ENABLE_MCP", "False").lower() in ("1", "true", "yes")
    MCP_TOOLS_JSON = os.getenv("MCP_TOOLS_JSON", "")  # path to JSON with tools schemas
    MCP_TIMEOUT_SECONDS = _env_int("MCP_TIMEOUT_SECONDS", 10)

    # === RAG / Embeddings (optional) ===
    ENABLE_RAG = os.getenv("ENABLE_RAG", "False").lower() in ("1", "true", "yes")
    RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "text-embedding-3-small")
    RAG_INDEX_PATH = os.getenv(
        "RAG_INDEX_PATH",
        os.path.join(os.path.dirname(__file__), "data", "rag_index.json"),
    )

    # === Voice / Realtime (optional) ===
    ENABLE_VOICE = os.getenv("ENABLE_VOICE", "False").lower() in ("1", "true", "yes")
    VOICE_MODEL = os.getenv("VOICE_MODEL", "gpt-4o-realtime")
    VOICE_MAX_SECONDS = _env_int("VOICE_MAX_SECONDS", 120)

    # === AI Gateway (optional, defaults to True) ===
    ENABLE_AI_GATEWAY = os.getenv("ENABLE_AI_GATEWAY", "True").lower() in ("1", "true", "yes")

    # Настройки для Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    # Настройки для Google Sheets, Drive и Calendar
    GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
    SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "1kyNQVjeLLe4Ra6oWuf84fHqSjUlWXI8MakVMOrCgic0")
    
    # Проверяем существование директории config
    CONFIG_DIR = os.path.join(os.path.dirname(__file__), "config")
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    
    GOOGLE_SERVICE_ACCOUNT_FILE = os.path.abspath(os.path.join(CONFIG_DIR, "service_account.json"))
    GOOGLE_WORKSHEET_NAME = "Dialog_History"

    # Настройки уведомлений
    NOTIFICATION_BOT_TOKEN = os.getenv("NOTIFICATION_BOT_TOKEN")
    TRAINER_CHAT_ID = os.getenv("TRAINER_CHAT_ID")

    CHAT_SYSTEM_PROMPT = "You are a helpful assistant."

    VERSION = "1.0.0"
    
    # Настройки для WakeSurf Challenge 2025
    WSC2025_ENABLED = os.getenv("WSC2025_ENABLED", "True").lower() in ("1", "true", "yes")
    WSC2025_SPREADSHEET_ID = os.getenv("WSC2025_SPREADSHEET_ID", SPREADSHEET_ID)
    WSC2025_PARTICIPANTS_SHEET = "WSC2025_Participants"
    WSC2025_COACHES_SHEET = "WSC2025_Coaches"
    
    # Настройки для Wake Surf Safari 2026
    SAFARI_SPREADSHEET_ID = os.getenv("SAFARI_SPREADSHEET_ID", os.getenv("SAFARI_TAB", SPREADSHEET_ID))
    
    # Rate limiting для форм регистрации
    RATELIMIT_STORAGE_URL = os.getenv("RATELIMIT_STORAGE_URL", "memory://")
    
    # CAPTCHA (опционально, можно добавить позже)
    RECAPTCHA_SITE_KEY = os.getenv("RECAPTCHA_SITE_KEY", "")
    RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", "")

class DevelopmentConfig(Config):
    """Конфигурация для разработки."""
    DEBUG = os.getenv('FLASK_DEBUG', 'False') == 'True'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///dev-app.db'
    SQLALCHEMY_ECHO = True  # Печать SQL-запросов в консоль

    # CSP для разработки
    CSP_POLICY = {
        'default-src': ["'self'"],
        'script-src': [
            "'self'",
            "'unsafe-eval'",
            "'unsafe-inline'",
            "https://cdn.jsdelivr.net",
            "https://cdnjs.cloudflare.com",
            "https://www.googletagmanager.com",
            "https://cdn.socket.io",
            "https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js",
            "https://mc.yandex.ru",
            "https://mc.yandex.com",
            "https://www.google-analytics.com"
        ],
        'style-src': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://cdn.jsdelivr.net", "https://cdnjs.cloudflare.com"],
        'style-src-elem': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://cdn.jsdelivr.net", "https://cdnjs.cloudflare.com"],
        'img-src': [
            "'self'",
            "https://cdn.jsdelivr.net",
            "https://cdnjs.cloudflare.com",
            "https://www.googletagmanager.com",
            "data:",
            "https://mc.yandex.ru",
            "https://mc.yandex.com"
        ],
        'font-src': [
            "'self'",
            "https://cdn.jsdelivr.net",
            "https://fonts.gstatic.com",
            "https://cdnjs.cloudflare.com"
        ],
        'connect-src': [
            "'self'",
            "https://cdn.jsdelivr.net",
            "https://cdnjs.cloudflare.com",
            "https://cdn.socket.io",
            "https://api.openai.com",
            "https://mc.yandex.com",
            "https://mc.yandex.ru",
            "wss://mc.yandex.com",
            "wss://mc.yandex.ru",
            "https://www.google-analytics.com"
        ],
        'frame-src': ["'self'", "https://cdn.jsdelivr.net", "https://calendar.google.com", "https://mc.yandex.com", "https://mc.yandex.ru"],
        'object-src': ["'none'"],
        'base-uri': ["'self'"],
        'form-action': ["'self'"],
        'frame-ancestors': ["'none'"],
        'upgrade-insecure-requests': [],
        'manifest-src': ["'self'"],
        'media-src': ["'self'"],
    }

class ProductionConfig(Config):
    """Конфигурация для продакшн."""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///app.db'
    SQLALCHEMY_ECHO = False  # Отключаем вывод SQL-запросов в продакшн

    # CSP для продакшена (более строгий)
    CSP_POLICY = {
        'default-src': ["'self'"],
        'script-src': [
            "'self'",
            "https://cdn.jsdelivr.net",
            "https://www.googletagmanager.com",
            "https://cdn.socket.io",
            "https://mc.yandex.ru",
            "https://mc.yandex.com",
            "https://www.google-analytics.com"
        ],
        'style-src': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://cdn.jsdelivr.net", "https://cdnjs.cloudflare.com"],
        'style-src-elem': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://cdn.jsdelivr.net", "https://cdnjs.cloudflare.com"],
        'img-src': [
            "'self'",
            "https://cdn.jsdelivr.net",
            "https://www.googletagmanager.com",
            "data:",
            "https://mc.yandex.ru",
            "https://mc.yandex.com"
        ],
        'font-src': [
            "'self'",
            "https://cdn.jsdelivr.net",
            "https://fonts.gstatic.com",
            "https://cdnjs.cloudflare.com"
        ],
        'connect-src': [
            "'self'",
            "https://cdn.jsdelivr.net",
            "https://cdn.socket.io",
            "https://api.openai.com",
            "https://mc.yandex.com",
            "https://mc.yandex.ru",
            "wss://mc.yandex.com",
            "wss://mc.yandex.ru",
            "https://www.google-analytics.com"
        ],
        'frame-src': ["'self'", "https://calendar.google.com", "https://mc.yandex.com", "https://mc.yandex.ru"],
        'object-src': ["'none'"],
        'base-uri': ["'self'"],
        'form-action': ["'self'"],
        'frame-ancestors': ["'none'"],
        'upgrade-insecure-requests': [],
        'manifest-src': ["'self'"],
        'media-src': ["'self'"],
    }
