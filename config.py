import os
from datetime import timedelta

class Config:
    """Основная конфигурация для приложения."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    ASSISTANT_ID = os.environ.get('ASSISTANT_ID')
    GOOGLE_CALENDAR_ID = os.environ.get('GOOGLE_CALENDAR_ID')
    SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
    TIMEZONE = 'Europe/Moscow'
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

    # Настройки для OpenAI и GPT
    GPTS_MODEL = os.getenv("GPTS_MODEL", "gpt-4")
    FINE_TUNED_MODEL = os.getenv("FINE_TUNED_MODEL", "ft:gpt-4o-mini-2024-07-18:mywave:mywavesite:Axgy7lSh")
    FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gpt-4o")

    # Настройки для Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    # Настройки для Google Sheets, Drive и Calendar
    GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
    GOOGLE_SERVICE_ACCOUNT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "configs", "service_account.json"))


    # Настройки уведомлений
    NOTIFICATION_BOT_TOKEN = os.getenv("NOTIFICATION_BOT_TOKEN")
    TRAINER_CHAT_ID = os.getenv("TRAINER_CHAT_ID")

class DevelopmentConfig(Config):
    """Конфигурация для разработки."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///dev-app.db'
    SQLALCHEMY_ECHO = True  # Печать SQL-запросов в консоль

class ProductionConfig(Config):
    """Конфигурация для продакшн."""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///app.db'
    SQLALCHEMY_ECHO = False  # Отключаем вывод SQL-запросов в продакшн
