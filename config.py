import os
from datetime import timedelta

class Config:
    """Основная конфигурация для приложения."""
    # SECRET_KEY обязателен в production; в development — желателен
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    GOOGLE_CALENDAR_ID = os.environ.get('GOOGLE_CALENDAR_ID')
    SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
    # Analytics sheet config (used for logging events and calculator history)
    ANALYTICS_SHEET_SPREADSHEET_ID = os.getenv("ANALYTICS_SHEET_SPREADSHEET_ID", "")
    ANALYTICS_SHEET_NAME = os.getenv("ANALYTICS_SHEET_NAME", "analytics_statistics")
    # Feature flags and recommendations tuning
    ENABLE_RECOMMENDATIONS = os.getenv('ENABLE_RECOMMENDATIONS', 'True') in ('1', 'true', 'True')
    ENABLE_ANALYTICS = os.getenv('ENABLE_ANALYTICS', 'True') in ('1', 'true', 'True')
    # A/B experiment split size (number of groups). Default 2 (A/B).
    AB_CONTROL_GROUP_SIZE = int(os.getenv('AB_CONTROL_GROUP_SIZE', '2'))
    # Recommendation cache time-to-live (seconds)
    RECO_CACHE_TTL = int(os.getenv('RECO_CACHE_TTL', '300'))
    # In-memory кэш строк raw_feed (Sheets) для витрины блога; 0 = всегда перечитывать
    BLOG_SHEETS_CACHE_TTL = int(os.getenv("BLOG_SHEETS_CACHE_TTL", "120"))
    # CSP toggle — allow enabling/disabling strict CSP rules via env
    CSP_ENABLED = os.getenv('CSP_ENABLED', 'True') in ('1', 'true', 'True')
    # Sitemap build timestamp (optional override)
    SITEMAP_BUILD_TS = os.getenv('SITEMAP_BUILD_TS', '')
    TIMEZONE = 'Europe/Moscow'
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    
    # Политика CSP по умолчанию (может быть переопределена в подклассах)
    CSP_POLICY = {}

    # Настройки для OpenAI и GPT
    GPTS_MODEL = os.getenv("GPTS_MODEL", "gpt-4.1-nano")
    FINE_TUNED_MODEL = os.getenv("FINE_TUNED_MODEL", "gpt-4.1-nano")
    FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gpt-4.1-nano")
    ASSISTANT_ID = os.getenv("ASSISTANT_ID")
    # Публичный чат (ask в openai_service): auto | completions | responses | assistant_only
    # auto — Assistant API при ASSISTANT_ID, иначе completions; при пустом ответе — fallback completions
    # completions — только Chat Completions + CHAT_SYSTEM_PROMPT (игнор ASSISTANT_ID)
    # responses — OpenAI Responses API для обычного public text chat
    # assistant_only — только Assistant API без fallback на completions (отладка)
    CHAT_BACKEND = (os.getenv("CHAT_BACKEND") or "auto").strip().lower()
    # Flask-Limiter: memory:// (локально), production — redis://host:6379/0
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")

    # Настройки для Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    # Настройки для Google Sheets, Drive и Calendar
    GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
    SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "1kyNQVjeLLe4Ra6oWuf84fHqSjUlWXI8MakVMOrCgic0")
    
    # Проверяем существование директории configs
    CONFIG_DIR = os.path.join(os.path.dirname(__file__), "configs")
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    
    GOOGLE_SERVICE_ACCOUNT_FILE = os.path.abspath(os.path.join(CONFIG_DIR, "service_account.json"))
    GOOGLE_WORKSHEET_NAME = "Dialog_History"

    # Public media upload (for parser -> site image publishing)
    SITE_BASE_URL = (os.getenv("SITE_BASE_URL") or "").rstrip("/")
    MEDIA_UPLOAD_TOKEN = os.getenv("MEDIA_UPLOAD_TOKEN", "")
    MEDIA_UPLOAD_SUBDIR = os.getenv("MEDIA_UPLOAD_SUBDIR", "uploads/review_media")
    MEDIA_UPLOAD_MAX_BYTES = int(os.getenv("MEDIA_UPLOAD_MAX_BYTES", "10485760"))
    # Optional absolute root for uploaded media (tests/local override).
    # If empty, uploads go to <static_folder>/<MEDIA_UPLOAD_SUBDIR>.
    MEDIA_UPLOAD_ROOT = os.getenv("MEDIA_UPLOAD_ROOT", "")

    # Настройки уведомлений
    NOTIFICATION_BOT_TOKEN = os.getenv("NOTIFICATION_BOT_TOKEN")
    TRAINER_CHAT_ID = os.getenv("TRAINER_CHAT_ID")

    CHAT_SYSTEM_PROMPT = "You are a helpful assistant."

    VERSION = "1.0.0"

class DevelopmentConfig(Config):
    """Конфигурация для разработки."""
    # В development допустим fallback для удобства; в production — обязательно из .env
    SECRET_KEY = os.getenv('SECRET_KEY') or 'dev-secret-key-change-in-production'
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
            "https://www.google-analytics.com",
            "https://*.googleapis.com"
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

class TestingConfig(Config):
    """Конфигурация для тестирования."""
    TESTING = True
    SECRET_KEY = os.getenv('SECRET_KEY') or 'test-secret-key-for-unit-tests'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # In-memory database для быстрых тестов
    SQLALCHEMY_ECHO = False
    WTF_CSRF_ENABLED = False  # Отключаем CSRF для тестов
    # Отключаем Google Sheets/Calendar в тестах — используем локальную БД
    SPREADSHEET_ID = os.getenv('TEST_SPREADSHEET_ID') or ''

class ProductionConfig(Config):
    """Конфигурация для продакшн."""
    _secret = os.getenv('SECRET_KEY')
    if not _secret or len(_secret) < 16:
        raise ValueError(
            "SECRET_KEY must be set in production (min 16 chars). "
            "Set it in .env or environment."
        )
    SECRET_KEY = _secret
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
