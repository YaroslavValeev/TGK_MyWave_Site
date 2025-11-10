"""
Конфигурация кэширования для Flask приложения
"""
import os
from datetime import timedelta

# Базовая конфигурация кэширования
CACHE_CONFIG = {
    'CACHE_TYPE': 'SimpleCache',  # Используем простое кэширование в памяти
    'CACHE_DEFAULT_TIMEOUT': 300,  # 5 минут
    'CACHE_THRESHOLD': 1000,  # Максимальное количество элементов в кэше,
    'CACHE_DIR': os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'cache')  # Для хранения изображений
}

# Конфигурация кэширования изображений
IMAGE_CACHE_CONFIG = {
    # Основные настройки
    'CACHE_IMAGES': True,
    'IMAGE_CACHE_DIR': os.path.join(CACHE_CONFIG['CACHE_DIR'], 'images'),
    'IMAGE_CACHE_TIMEOUT': int(timedelta(days=7).total_seconds()),  # 7 дней
    
    # Настройки кэширования
    'CACHE_CONTROL': 'public, max-age=604800',  # 7 дней
    'EXPIRES_IN': 604800,  # 7 дней в секундах
    'VARY_ACCEPT_ENCODING': True,  # Учитывать заголовок Accept-Encoding
    
    # Оптимизация изображений
    'OPTIMIZE_IMAGES': True,
    'DEFAULT_JPEG_QUALITY': 85,
    'DEFAULT_PNG_COMPRESSION': 6,
    'DEFAULT_WEBP_QUALITY': 80,
    'MAX_IMAGE_SIZE': 10 * 1024 * 1024,  # 10 МБ
    
    # Размеры для респонсивных изображений
    'RESPONSIVE_SIZES': {
        'thumbnail': (150, 150),
        'small': (800, 600),
        'medium': (1024, 768),
        'large': (1920, 1440),
        'xlarge': (2560, 1920)
    }
}

# Разрешенные расширения для изображений
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Создаем директории для кэширования если они не существуют
os.makedirs(CACHE_CONFIG['CACHE_DIR'], exist_ok=True)
os.makedirs(IMAGE_CACHE_CONFIG['IMAGE_CACHE_DIR'], exist_ok=True)

# Заголовки кэширования для статических файлов
STATIC_CACHE_HEADERS = {
    'Cache-Control': 'public, max-age=31536000',  # 1 год
    'Vary': 'Accept-Encoding'
}

# Конфигурация CDN (если используется)
CDN_CONFIG = {
    'ENABLED': False,
    'DOMAIN': None,
    'HTTPS': True
}