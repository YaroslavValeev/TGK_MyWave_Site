"""
Утилиты для кэширования и обработки изображений
"""
import os
import hashlib
from functools import wraps
from io import BytesIO
from PIL import Image
from flask import send_file, request, current_app
from werkzeug.utils import secure_filename
from app.extensions import cache
from app.config.cache_config import IMAGE_CACHE_CONFIG

def get_image_cache_key(path, width=None, height=None, format=None, size=None):
    """
    Генерирует ключ кэша для изображения с учетом параметров
    """
    cache_key = f"img:{path}"
    if width:
        cache_key += f":w{width}"
    if height:
        cache_key += f":h{height}"
    if size:
        cache_key += f":s{size[0]}x{size[1]}"
    if format:
        cache_key += f":f{format}"
    return f"image_cache_{hashlib.md5(cache_key.encode()).hexdigest()}"

def cache_image(timeout=None):
    """
    Декоратор для кэширования изображений
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not IMAGE_CACHE_CONFIG.get('CACHE_IMAGES', True):
                return f(*args, **kwargs)

            # Получаем ключ кэша на основе пути и параметров
            cache_key = get_image_cache_key(
                request.path,
                request.args.get('w'),
                request.args.get('h'),
                request.args.get('format'),
                kwargs.get('size')
            )
            
            # Пробуем получить из кэша
            cached_image = cache.get(cache_key)
            if cached_image:
                return send_file(
                    BytesIO(cached_image),
                    mimetype=get_mimetype(request.args.get('format', 'jpeg')),
                    max_age=IMAGE_CACHE_CONFIG.get('IMAGE_CACHE_TIMEOUT', 604800)
                )
                
            # Если нет в кэше - обрабатываем
            response = f(*args, **kwargs)
            
            # Кэшируем только если это объект response с изображением
            if hasattr(response, 'get_data'):
                timeout_value = timeout or IMAGE_CACHE_CONFIG.get('IMAGE_CACHE_TIMEOUT', 604800)
                cache.set(cache_key, response.get_data(), timeout=timeout_value)
            
            return response
            
        return decorated_function
    return decorator

def get_mimetype(format):
    """
    Возвращает MIME-тип для формата изображения
    """
    format = format.lower()
    mimetypes = {
        'jpeg': 'image/jpeg',
        'jpg': 'image/jpeg',
        'png': 'image/png',
        'webp': 'image/webp',
        'gif': 'image/gif'
    }
    return mimetypes.get(format, 'application/octet-stream')

def optimize_image(image, format='WEBP', quality=None):
    """
    Оптимизирует изображение и возвращает BytesIO объект
    """
    if quality is None:
        quality = IMAGE_CACHE_CONFIG.get('DEFAULT_WEBP_QUALITY', 80)
    
    output = BytesIO()
    format = format.upper()
    
    # Проверяем режим изображения
    if image.mode in ('RGBA', 'LA') and format != 'PNG':
        background = Image.new('RGB', image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1])
        image = background
    
    # Оптимизируем в зависимости от формата
    if format == 'JPEG':
        image.save(output, format=format, quality=quality, optimize=True, progressive=True)
    elif format == 'PNG':
        image.save(output, format=format, optimize=True, 
                  compress_level=IMAGE_CACHE_CONFIG.get('DEFAULT_PNG_COMPRESSION', 6))
    elif format == 'WEBP':
        image.save(output, format=format, quality=quality, method=6, lossless=False)
    else:
        image.save(output, format=format)
    
    output.seek(0)
    return output

def resize_image(image_path, width=None, height=None, format='WEBP', size=None):
    """
    Изменяет размер изображения с сохранением пропорций
    """
    with Image.open(image_path) as img:
        # Получаем текущие размеры
        img_w, img_h = img.size
        
        # Определяем новый размер
        if size:
            width, height = size
        
        # Вычисляем новые размеры с сохранением пропорций
        if width and height:
            ratio = min(width/img_w, height/img_h)
            new_size = (int(img_w * ratio), int(img_h * ratio))
        elif width:
            ratio = width/img_w
            new_size = (width, int(img_h * ratio))
        elif height:
            ratio = height/img_h
            new_size = (int(img_w * ratio), height)
        else:
            new_size = None
            
        # Изменяем размер если нужно
        if new_size:
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Оптимизируем и возвращаем
        return optimize_image(img, format=format)

def get_image_info(image_path):
    """
    Получает информацию об изображении
    """
    try:
        with Image.open(image_path) as img:
            return {
                'format': img.format,
                'mode': img.mode,
                'size': img.size,
                'width': img.width,
                'height': img.height
            }
    except Exception as e:
        current_app.logger.error(f"Error getting image info for {image_path}: {str(e)}")
        raise

def clean_image_cache():
    """
    Очищает кэш изображений
    """
    try:
        pattern = "image_cache_*"
        keys = [k for k in cache.cache._cache.keys() if k.startswith("image_cache_")]
        for key in keys:
            cache.delete(key)
        return True
    except Exception as e:
        current_app.logger.error(f"Error cleaning image cache: {str(e)}")
        return False