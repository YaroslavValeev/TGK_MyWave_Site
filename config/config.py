"""
Конфигурация приложения
"""

import os


class Config:
    # Flask базовые настройки
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-key"
    DEBUG = False
    TESTING = False

    # Директории для загрузки файлов
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB макс размер файла

    # Настройки кэширования
    CACHE_TYPE = "filesystem"
    CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_THRESHOLD = 1000
    CACHE_OPTIONS = {"mode": 0o600}

    # Настройки для изображений
    IMAGE_CACHE_CONFIG = {
        "CACHE_CONTROL": "public, max-age=31536000",  # 1 год
        "EXPIRES_IN": 31536000,  # 1 год в секундах
        "VARY_ACCEPT_ENCODING": True,
    }


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    # Продакшн настройки
    DEBUG = False
    # Рекомендуется использовать переменные окружения для секретов
    SECRET_KEY = os.environ.get("SECRET_KEY")
