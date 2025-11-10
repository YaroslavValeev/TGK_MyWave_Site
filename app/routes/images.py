"""
Обработка маршрутов для изображений с поддержкой кэширования и оптимизации
"""
import os
from io import BytesIO
from flask import Blueprint, send_file, request, current_app, abort, make_response
from werkzeug.utils import secure_filename
from app.utils.image_cache import (
    cache_image, resize_image, optimize_image, get_image_info,
    get_mimetype, clean_image_cache
)
from app.config.cache_config import (
    ALLOWED_IMAGE_EXTENSIONS,
    IMAGE_CACHE_CONFIG
)

# Создаем Blueprint для изображений
images = Blueprint('images', __name__)

def allowed_file(filename):
    """Проверяет допустимое ли расширение у файла"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def get_best_format(accept_header):
    """
    Определяет лучший формат изображения на основе Accept заголовка
    """
    if not accept_header:
        return 'webp'

    formats = {
        'image/webp': 'webp',
        'image/jpeg': 'jpeg',
        'image/png': 'png'
    }
    
    # Проверяем поддержку WebP
    if 'image/webp' in accept_header:
        return 'webp'
    # Fallback к JPEG
    return 'jpeg'

@images.route('/images/<path:filename>')
@cache_image()
def serve_image(filename):
    """
    Отдает изображение с учетом параметров ресайза и кэширования
    Поддерживает:
    - Изменение размера (w, h параметры)
    - Автоматический выбор формата (webp для поддерживающих браузеров)
    - Оптимизацию изображений
    - Кэширование
    """
    if not allowed_file(filename):
        abort(404)
        
    try:
        # Получаем параметры изображения
        width = request.args.get('w', type=int)
        height = request.args.get('h', type=int)
        size = (width, height) if width and height else None
        
        # Определяем формат
        requested_format = request.args.get('format')
        if requested_format:
            img_format = requested_format.upper()
        else:
            img_format = get_best_format(request.headers.get('Accept')).upper()
        
        # Проверяем существование файла
        image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(filename))
        if not os.path.isfile(image_path):
            abort(404)
        
        # Получаем информацию об изображении
        image_info = get_image_info(image_path)
        
        # Проверяем размер файла
        if os.path.getsize(image_path) > IMAGE_CACHE_CONFIG['MAX_IMAGE_SIZE']:
            abort(413)  # Payload Too Large
        
        # Обрабатываем изображение
        image_data = resize_image(image_path, size=size, format=img_format)
        
        # Создаем ответ
        response = make_response(send_file(
            image_data,
            mimetype=get_mimetype(img_format.lower()),
            max_age=IMAGE_CACHE_CONFIG['IMAGE_CACHE_TIMEOUT'],
            as_attachment=False
        ))
        
        # Добавляем заголовки
        response.headers['Cache-Control'] = IMAGE_CACHE_CONFIG.get('CACHE_CONTROL', 'public, max-age=604800')
        if IMAGE_CACHE_CONFIG.get('VARY_ACCEPT_ENCODING', True):
            response.headers['Vary'] = 'Accept-Encoding'
            
        # Добавляем информацию об изображении
        response.headers['X-Image-Original-Size'] = f"{image_info['width']}x{image_info['height']}"
        response.headers['X-Image-Format'] = img_format
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error processing image {filename}: {str(e)}")
        abort(500)

@images.route('/admin/images/clear-cache', methods=['POST'])
def clear_image_cache():
    """
    Очищает кэш изображений
    """
    try:
        if clean_image_cache():
            return {'status': 'success', 'message': 'Image cache cleared'}, 200
        return {'status': 'error', 'message': 'Failed to clear image cache'}, 500
    except Exception as e:
        current_app.logger.error(f"Error clearing image cache: {str(e)}")
        return {'status': 'error', 'message': str(e)}, 500