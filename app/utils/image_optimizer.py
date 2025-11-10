"""
Утилиты для работы с изображениями
"""

from PIL import Image, ImageOps
import os

def optimize_image(filepath: str, quality: int = 85, max_size: tuple = None):
    """
    Оптимизирует изображение для веба
    
    Args:
        filepath (str): Путь к файлу
        quality (int): Качество JPEG (1-100)
        max_size (tuple): Максимальный размер (width, height)
    """
    try:
        with Image.open(filepath) as img:
            # Конвертируем в RGB если нужно
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Изменяем размер если задан максимум
            if max_size:
                img.thumbnail(max_size, Image.LANCZOS)
            
            # Автоповорот на основе EXIF
            img = ImageOps.exif_transpose(img)
            
            # Сохраняем с оптимизацией
            img.save(filepath, 'JPEG',
                    quality=quality,
                    optimize=True,
                    progressive=True)
            
            return True
    except Exception as e:
        print(f"Ошибка оптимизации {filepath}: {e}")
        return False

def create_thumbnail(source: str, dest: str, size: tuple):
    """
    Создает миниатюру изображения
    
    Args:
        source (str): Путь к исходному файлу
        dest (str): Путь для сохранения миниатюры
        size (tuple): Размер миниатюры (width, height)
    """
    try:
        with Image.open(source) as img:
            # Создаем миниатюру
            thumb = ImageOps.fit(img, size, Image.LANCZOS)
            
            # Сохраняем
            thumb.save(dest, 'JPEG',
                      quality=85,
                      optimize=True)
            
            return True
    except Exception as e:
        print(f"Ошибка создания миниатюры {source}: {e}")
        return False

def get_image_dimensions(filepath: str) -> tuple:
    """
    Возвращает размеры изображения (width, height)
    """
    try:
        with Image.open(filepath) as img:
            return img.size
    except:
        return (0, 0)