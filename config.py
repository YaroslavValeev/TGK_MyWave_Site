import os

class Config:
    """Основная конфигурация для приложения."""
    # Базовые настройки базы данных
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "maOg1l0Kc"

    # Настройки для OpenAI и GPT
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GPTS_MODEL = os.getenv("GPTS_MODEL", "gpt-4")
    FINE_TUNED_MODEL = os.getenv("FINE_TUNED_MODEL", "ft:gpt-4o-mini-2024-07-18:mywave:mywavesite:Axgy7lSh")
    FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gpt-4o")

    # Настройки для Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    # Настройки для Google Sheets, Drive и Calendar
    GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
    GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")
    DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
    GOOGLE_SERVICE_ACCOUNT_FILE = "configs/service_account.json"

    # Настройки уведомлений
    NOTIFICATION_BOT_TOKEN = os.getenv("NOTIFICATION_BOT_TOKEN")
    TRAINER_CHAT_ID = os.getenv("TRAINER_CHAT_ID")

class DevelopmentConfig(Config):
    """Конфигурация для разработки."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///mywave.db")
    SQLALCHEMY_ECHO = True  # Печать SQL-запросов в консоль

class ProductionConfig(Config):
    """Конфигурация для продакшн."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///mywave.db")
    SQLALCHEMY_ECHO = False  # Отключаем вывод SQL-запросов в продакшн
