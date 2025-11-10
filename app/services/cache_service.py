from flask import current_app
from flask_caching import Cache

cache = Cache(config={
    'CACHE_TYPE': 'simple',  # Для разработки используем простой кэш в памяти
    'CACHE_DEFAULT_TIMEOUT': 300  # 5 минут по умолчанию
})

def init_cache(app):
    """Инициализация сервиса кэширования"""
    cache.init_app(app)
    return cache

def cache_static(response):
    """Добавляет заголовки кэширования для статических файлов"""
    if response.mimetype in ['image/jpeg', 'image/png', 'image/webp']:
        response.cache_control.max_age = 3600 * 24 * 7  # 7 дней
        response.cache_control.public = True
    return response