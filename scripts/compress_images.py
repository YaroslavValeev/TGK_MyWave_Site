"""Утилита для оптимизации изображений"""
import os
from PIL import Image
import sys
from pathlib import Path

def compress_image(image_path, output_path=None, quality=85):
    """Сжимает изображение с сохранением приемлемого качества"""
    if output_path is None:
        output_path = image_path
        
    try:
        # Открываем изображение
        with Image.open(image_path) as img:
            # Конвертируем в RGB если нужно
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
                
            # Оптимизируем и сохраняем
            img.save(output_path, 'JPEG', quality=quality, optimize=True)
            
        original_size = os.path.getsize(image_path)
        compressed_size = os.path.getsize(output_path)
        saved = original_size - compressed_size
        saved_percent = (saved / original_size) * 100 if original_size > 0 else 0
        
        print(f"Сжатие {os.path.basename(image_path)}:")
        print(f"  Исходный размер: {original_size / 1024:.1f} KB")
        print(f"  Новый размер: {compressed_size / 1024:.1f} KB")
        print(f"  Экономия: {saved / 1024:.1f} KB ({saved_percent:.1f}%)")
        
        return True
    except Exception as e:
        print(f"Ошибка при сжатии {image_path}: {e}")
        return False

def compress_directory(input_dir, output_dir=None, quality=85):
    """Сжимает все изображения в директории"""
    input_dir = Path(input_dir)
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    total_saved = 0
    total_files = 0
    failed_files = 0
    
    for file_path in input_dir.glob('**/*'):
        if file_path.suffix.lower() in {'.jpg', '.jpeg', '.png'}:
            if output_dir:
                rel_path = file_path.relative_to(input_dir)
                out_path = output_dir / rel_path
                out_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                out_path = file_path
                
            print(f"\nОбработка: {file_path.name}")
            
            original_size = file_path.stat().st_size
            if compress_image(str(file_path), str(out_path), quality):
                total_files += 1
                compressed_size = out_path.stat().st_size
                total_saved += (original_size - compressed_size)
            else:
                failed_files += 1
    
    print("\nИтоги сжатия:")
    print(f"Обработано файлов: {total_files}")
    print(f"Ошибок: {failed_files}")
    print(f"Общая экономия: {total_saved / 1024 / 1024:.1f} MB")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование:")
        print("python compress_images.py путь/к/папке [путь/к/выходной/папке] [качество]")
        sys.exit(1)
        
    input_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    quality = int(sys.argv[3]) if len(sys.argv) > 3 else 85
    
    compress_directory(input_dir, output_dir, quality)