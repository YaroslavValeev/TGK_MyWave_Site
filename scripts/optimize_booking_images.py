from PIL import Image
import os

def optimize_image(input_path, output_path, target_width=800):
    """Оптимизирует изображение для веб-использования"""
    with Image.open(input_path) as img:
        # Сохраняем пропорции
        width_percent = (target_width / float(img.size[0]))
        target_height = int((float(img.size[1]) * float(width_percent)))
        
        # Изменяем размер
        img_resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        # Конвертируем в WebP с хорошим качеством
        img_resized.save(output_path, 'WEBP', quality=85, optimize=True)

def main():
    # Создаем директорию если её нет
    output_dir = '../static/images/booking'
    os.makedirs(output_dir, exist_ok=True)
    
    # Определяем преобразования
    conversions = {
        'boat.jpg': 'dock-experience-v1.webp',  # Катер на воде
        'gym.jpg': 'gym-experience-v1.webp',    # Фото зала
        'boat-gear.jpg': 'gear-checklist-v1.webp',  # Фото снаряжения
        'sketch.jpg': 'wake-experience-v1.webp'  # Скетч для Wake Discovery
    }
    
    for input_file, output_file in conversions.items():
        input_path = os.path.join('temp_images', input_file)
        output_path = os.path.join(output_dir, output_file)
        try:
            optimize_image(input_path, output_path)
            print(f"✓ Создано: {output_file}")
        except Exception as e:
            print(f"✕ Ошибка при обработке {input_file}: {str(e)}")

if __name__ == '__main__':
    main()