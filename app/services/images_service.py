"""Сервис для работы с изображениями"""

import os
from PIL import Image
from io import BytesIO
from datetime import datetime
from app.services.cache_service import cache

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
SIZES = {
    "thumb": (150, 150),
    "small": (300, 300),
    "medium": (600, 600),
    "large": (1200, 1200),
}


def allowed_file(filename):
    """Проверяет допустимость расширения файла"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(file, folder):
    """Сохраняет изображение и создает его миниатюры"""
    if not file or not allowed_file(file.filename):
        return None

    # Генерируем уникальное имя файла
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(folder, filename)

    # Сохраняем оригинал
    file.save(file_path)

    # Создаем различные размеры
    create_image_sizes(file_path)

    return filename


def create_image_sizes(original_path):
    """Создает миниатюры разных размеров"""
    filename = os.path.basename(original_path)
    folder = os.path.dirname(original_path)

    with Image.open(original_path) as img:
        for size_name, dimensions in SIZES.items():
            size_folder = os.path.join(folder, size_name)
            os.makedirs(size_folder, exist_ok=True)

            # Создаем копию нужного размера
            copy = img.copy()
            copy.thumbnail(dimensions)

            # Сохраняем в соответствующую папку
            size_path = os.path.join(size_folder, filename)
            copy.save(size_path, optimize=True, quality=85)


def get_image_url(image_name, size="medium"):
    """Возвращает URL изображения нужного размера"""
    if not image_name:
        return None

    @cache.memoize(timeout=3600)
    def _get_image_url(image_name, size):
        base_url = "/static/images"
        if size in SIZES:
            return f"{base_url}/{size}/{image_name}"
        return f"{base_url}/{image_name}"

    return _get_image_url(image_name, size)
