import os
from datetime import timedelta


BASE_DIR = os.path.dirname(__file__)
CONFIG_DIR_PATH = os.path.join(BASE_DIR, "configs")


def _clean_url(value) -> str:
    return (value or "").strip().rstrip("/")


def _resolve_public_base_url() -> str:
    return _clean_url(os.getenv("PUBLIC_BASE_URL") or os.getenv("BASE_URL"))


def _resolve_site_base_url() -> str:
    return _clean_url(os.getenv("SITE_BASE_URL") or _resolve_public_base_url())


def _resolve_server_name() -> str:
    return (os.getenv("SERVER_NAME") or os.getenv("DOMAIN") or "").strip()


def _resolve_healthcheck_url() -> str:
    explicit = _clean_url(os.getenv("HEALTHCHECK_URL"))
    if explicit:
        return explicit
    public_base_url = _resolve_public_base_url()
    if public_base_url:
        return f"{public_base_url}/health"
    return ""


def _resolve_service_account_file() -> str:
    """Путь к JSON сервисного аккаунта Google.

    Если в .env указан путь, но файла нет (типично Docker: SA в volume instance/),
    перебираем стандартные расположения и берём первый существующий.
    """
    candidates = []
    for env_key in ("GOOGLE_SERVICE_ACCOUNT_FILE", "GOOGLE_SHEETS_CREDENTIALS", "GOOGLE_APPLICATION_CREDENTIALS"):
        env_path = (os.getenv(env_key) or "").strip()
        if env_path:
            candidates.append(os.path.abspath(env_path))
    candidates.extend([
        os.path.join(CONFIG_DIR_PATH, "service_account.json"),
        os.path.join(BASE_DIR, "instance", "service_account.json"),
        os.path.join(BASE_DIR, "service_account.json"),
    ])
    seen = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        if os.path.isfile(path):
            return path
    return candidates[0] if candidates else os.path.join(CONFIG_DIR_PATH, "service_account.json")


def _sqlite_file_url(path: str) -> str:
    normalized = os.path.abspath(path).replace("\\", "/")
    if os.name == "nt":
        return f"sqlite:///{normalized}"
    return f"sqlite:////{normalized.lstrip('/')}"


def _default_production_database_url() -> str:
    return _sqlite_file_url(os.path.join(BASE_DIR, "instance", "mywave.db"))

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
    COMPETITIONS_SHEET_NAME = os.getenv("COMPETITIONS_SHEET_NAME", "competitions_ticker")
    COMPETITIONS_SHEETS_CACHE_TTL = int(os.getenv("COMPETITIONS_SHEETS_CACHE_TTL", "300"))
    # CSP toggle — allow enabling/disabling strict CSP rules via env
    CSP_ENABLED = os.getenv('CSP_ENABLED', 'True') in ('1', 'true', 'True')
    # GA / Yandex Metrika / GTM: выключены по умолчанию для dev/testing; включаются в ProductionConfig или явным env=1
    ENABLE_PUBLIC_ANALYTICS = False
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
    OPENAI_HTTP_PROXY = os.getenv("OPENAI_HTTP_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    # Публичный чат (ask в openai_service): auto | completions | responses | assistant_only
    # completions (рекомендуется для сайта) — Chat Completions + CHAT_SYSTEM_PROMPT + KB
    # auto — completions, кроме случая CHAT_USE_ASSISTANT=1 + ASSISTANT_ID (legacy Assistant)
    # responses — OpenAI Responses API для обычного public text chat
    # assistant_only — только Assistant API без fallback на completions (отладка)
    CHAT_BACKEND = (os.getenv("CHAT_BACKEND") or "completions").strip().lower()
    CHAT_USE_ASSISTANT = os.getenv("CHAT_USE_ASSISTANT", "").strip().lower() in ("1", "true", "yes")
    # Flask-Limiter: memory:// (локально), production — redis://host:6379/0
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")

    # Настройки для Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")

    # Настройки для Google Sheets, Drive и Calendar
    GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS") or os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
    SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
    # Блог / Parser News (raw_feed). Отдельно от SPREADSHEET_ID (Admin/Tg Bot, tail …OrCgic0).
    # Канон: docs/integration/SHEETS_ID_CANON.md
    PARSER_NEWS_SPREADSHEET_ID = os.getenv("PARSER_NEWS_SPREADSHEET_ID", "")
    PARSER_SHEET_NAME = os.getenv("PARSER_SHEET_NAME", "raw_feed")
    CLIENT_WORKOUTS_SHEET_NAME = os.getenv("CLIENT_WORKOUTS_SHEET_NAME", "Client_Workouts")
    BOAT_BOOKINGS_SHEET_NAME = os.getenv("BOAT_BOOKINGS_SHEET_NAME", "Boat_Bookings")
    BOAT_RUZA_SYNC_ENABLED = os.getenv("BOAT_RUZA_SYNC_ENABLED", "False") in ("1", "true", "True")
    BOAT_RUZA_SPREADSHEET_ID = os.getenv("BOAT_RUZA_SPREADSHEET_ID", "")
    BOAT_RUZA_CLUB_ID = os.getenv("BOAT_RUZA_CLUB_ID", "ice_beach_ruza")
    BOAT_RUZA_CLIENTS_SHEET_NAME = os.getenv("BOAT_RUZA_CLIENTS_SHEET_NAME", "clients")
    BOAT_RUZA_BOOKINGS_SHEET_NAME = os.getenv("BOAT_RUZA_BOOKINGS_SHEET_NAME", "bookings")
    BOAT_RUZA_BOATS_SHEET_NAME = os.getenv("BOAT_RUZA_BOATS_SHEET_NAME", "boats")
    BOAT_RUZA_SCHEDULE_SHEET_NAME = os.getenv("BOAT_RUZA_SCHEDULE_SHEET_NAME", "schedule")
    BOAT_RUZA_SLOT_OVERRIDES_SHEET_NAME = os.getenv("BOAT_RUZA_SLOT_OVERRIDES_SHEET_NAME", "slot_overrides")
    BOAT_RUZA_AUDIT_LOG_SHEET_NAME = os.getenv("BOAT_RUZA_AUDIT_LOG_SHEET_NAME", "audit_log")
    BOAT_RUZA_DEFAULT_BOAT_ID = os.getenv("BOAT_RUZA_DEFAULT_BOAT_ID", "boat_001")
    BOAT_RUZA_DEFAULT_BOOKING_STATUS = os.getenv("BOAT_RUZA_DEFAULT_BOOKING_STATUS", "new")
    BOAT_RUZA_DEFAULT_RIDE_TYPE = os.getenv("BOAT_RUZA_DEFAULT_RIDE_TYPE", "surf")
    BOAT_RUZA_TOTAL_PRICE = os.getenv("BOAT_RUZA_TOTAL_PRICE", "10000")
    BOAT_RUZA_CREATED_BY = os.getenv("BOAT_RUZA_CREATED_BY", "site")
    HOME_BOOKING_SWITCH_DATE = os.getenv("HOME_BOOKING_SWITCH_DATE", "2026-05-15")
    HOME_BOOKING_DEFAULT_SERVICE = os.getenv("HOME_BOOKING_DEFAULT_SERVICE", "gym")
    HOME_BOOKING_SWITCHED_SERVICE = os.getenv("HOME_BOOKING_SWITCHED_SERVICE", "boat")

    # MyWave Social Mission (default OFF — Social-1 data layer only)
    SOCIAL_SPREADSHEET_ID = os.getenv("SOCIAL_SPREADSHEET_ID", "")
    SOCIAL_APPLICATIONS_SHEET_NAME = os.getenv("SOCIAL_APPLICATIONS_SHEET_NAME", "Social_Applications")
    SOCIAL_SESSIONS_SHEET_NAME = os.getenv("SOCIAL_SESSIONS_SHEET_NAME", "Social_Sessions")
    SOCIAL_IMPACT_SHEET_NAME = os.getenv("SOCIAL_IMPACT_SHEET_NAME", "Social_Impact")
    SOCIAL_AUDIT_LOG_SHEET_NAME = os.getenv("SOCIAL_AUDIT_LOG_SHEET_NAME", "Social_Audit_Log")
    ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
    
    # Проверяем существование директории configs
    CONFIG_DIR = CONFIG_DIR_PATH
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    
    GOOGLE_SERVICE_ACCOUNT_FILE = _resolve_service_account_file()
    GOOGLE_WORKSHEET_NAME = "Dialog_History"

    # Public media upload (for parser -> site image publishing)
    DOMAIN = (os.getenv("DOMAIN") or "").strip()
    BASE_URL = _clean_url(os.getenv("BASE_URL"))
    PUBLIC_BASE_URL = _resolve_public_base_url()
    SITE_BASE_URL = _resolve_site_base_url()
    SERVER_NAME = _resolve_server_name()
    HEALTHCHECK_URL = _resolve_healthcheck_url()
    MEDIA_UPLOAD_TOKEN = os.getenv("MEDIA_UPLOAD_TOKEN", "")
    # Опционально: отдельный токен для invalidate competitions (иначе — MEDIA_UPLOAD_TOKEN)
    COMPETITIONS_CACHE_INVALIDATE_TOKEN = os.getenv("COMPETITIONS_CACHE_INVALIDATE_TOKEN", "")
    MEDIA_UPLOAD_SUBDIR = os.getenv("MEDIA_UPLOAD_SUBDIR", "uploads/review_media")
    MEDIA_UPLOAD_MAX_BYTES = int(os.getenv("MEDIA_UPLOAD_MAX_BYTES", "10485760"))
    # Optional absolute root for uploaded media (tests/local override).
    # If empty, uploads go to <static_folder>/<MEDIA_UPLOAD_SUBDIR>.
    MEDIA_UPLOAD_ROOT = os.getenv("MEDIA_UPLOAD_ROOT", "")

    # Настройки уведомлений
    NOTIFICATION_BOT_TOKEN = os.getenv("NOTIFICATION_BOT_TOKEN")
    TRAINER_CHAT_ID = os.getenv("TRAINER_CHAT_ID")

    # WakeSurf Challenge 2025
    WSC2025_SPREADSHEET_ID = os.getenv("WSC2025_SPREADSHEET_ID") or os.getenv("SPREADSHEET_ID", "")
    WSC2025_PARTICIPANTS_SHEET = os.getenv("WSC2025_PARTICIPANTS_SHEET", "WSC2025_Participants")
    WSC2025_COACHES_SHEET = os.getenv("WSC2025_COACHES_SHEET", "WSC2025_Coaches")
    WSC_ADMIN_EMAIL = os.getenv("WSC_ADMIN_EMAIL", "y.valeev@gmail.com")
    SAFARI_SPREADSHEET_ID = os.getenv("SAFARI_SPREADSHEET_ID") or os.getenv("SPREADSHEET_ID", "")

    # SMTP (опционально, для email-уведомлений о заявках WSC и др.)
    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True").lower() in ("1", "true", "yes")
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@mywavewake.ru")

    CHAT_SYSTEM_PROMPT = "You are a helpful assistant."

    VERSION = "1.0.0"

class DevelopmentConfig(Config):
    """Конфигурация для разработки."""
    # В development допустим fallback для удобства; в production — обязательно из .env
    SECRET_KEY = os.getenv('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.getenv('FLASK_DEBUG', 'False') == 'True'
    # Локально при 127.0.0.1 обычно не нужна внешняя аналитика (консоль + CSP без шума).
    ENABLE_PUBLIC_ANALYTICS = os.getenv('ENABLE_PUBLIC_ANALYTICS', '0').lower() in ('1', 'true', 'yes')
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
            # Обложки блога приходят из произвольных внешних CMS/CDN (СМИ).
            # Безопаснее разрешить https:/http: целиком, чем держать allowlist
            # десятков случайных доменов и постоянно расширять его руками.
            "https:",
            "http:",
            "data:",
            "blob:",
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
            "https://www.googletagmanager.com",
            "https://www.google.com",
            "https://analytics.google.com",
            "https://*.google-analytics.com",
            "https://*.analytics.google.com",
            "https://*.googleapis.com"
        ],
        'frame-src': [
            "'self'",
            "https://cdn.jsdelivr.net",
            "https://calendar.google.com",
            "https://mc.yandex.com",
            "https://mc.yandex.ru",
            "https://www.youtube.com",
            "https://www.youtube-nocookie.com",
            "https://*.youtube.com",
            "https://player.vimeo.com"
        ],
        'object-src': ["'none'"],
        'base-uri': ["'self'"],
        'form-action': ["'self'"],
        'frame-ancestors': ["'none'"],
        'upgrade-insecure-requests': [],
        'manifest-src': ["'self'"],
        'media-src': ["'self'", "blob:"],
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
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or _default_production_database_url()
    SQLALCHEMY_ECHO = False  # Отключаем вывод SQL-запросов в продакшн

    # Публичная аналитика: по умолчанию следует ENABLE_ANALYTICS; отключить FORCE: ENABLE_PUBLIC_ANALYTICS=0
    ENABLE_PUBLIC_ANALYTICS = Config.ENABLE_ANALYTICS and os.getenv(
        'ENABLE_PUBLIC_ANALYTICS', '1'
    ).lower() not in ('0', 'false', 'no')

    # CSP для продакшена (строгая, но с разрешёнными origins для счётчиков и картинок блога)
    CSP_POLICY = {
        'default-src': ["'self'"],
        'script-src': [
            "'self'",
            "https://cdn.jsdelivr.net",
            "https://cdnjs.cloudflare.com",
            "https://www.googletagmanager.com",
            "https://cdn.socket.io",
            "https://mc.yandex.ru",
            "https://mc.yandex.com",
            "https://www.google-analytics.com",
            "https://www.google.com"
        ],
        'style-src': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://cdn.jsdelivr.net", "https://cdnjs.cloudflare.com"],
        'style-src-elem': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://cdn.jsdelivr.net", "https://cdnjs.cloudflare.com"],
        'img-src': [
            "'self'",
            # Обложки блога: внешние CMS/CDN (см. комментарий в DevelopmentConfig).
            "https:",
            "data:",
            "blob:",
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
            "https://www.googletagmanager.com",
            "https://www.google.com",
            "https://analytics.google.com",
            "https://*.google-analytics.com",
            "https://*.analytics.google.com"
        ],
        'frame-src': [
            "'self'",
            "https://calendar.google.com",
            "https://mc.yandex.com",
            "https://mc.yandex.ru",
            "https://www.youtube.com",
            "https://www.youtube-nocookie.com",
            "https://*.youtube.com",
            "https://player.vimeo.com"
        ],
        'media-src': ["'self'", "blob:", "https://*.googlevideo.com"],
        'object-src': ["'none'"],
        'base-uri': ["'self'"],
        'form-action': ["'self'"],
        'frame-ancestors': ["'none'"],
        'upgrade-insecure-requests': [],
        'manifest-src': ["'self'"],
    }
