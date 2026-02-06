import shutil
import os
from pathlib import Path


def copy_and_rename_images():
    # Исходные изображения (предполагаем, что они уже загружены в static/images)
    source_images = {
        "nautique.jpg": "boat.jpg",  # Фото катера
        "gym_training.jpg": "gym.jpg",  # Фото зала
        "surf_gear.jpg": "boat-gear.jpg",  # Фото снаряжения
        "wake_sketch.jpg": "sketch.jpg",  # Скетч
    }

    # Пути
    script_dir = Path(__file__).parent
    temp_dir = script_dir / "temp_images"
    static_dir = script_dir.parent / "static" / "images"

    # Создаем временную директорию если её нет
    temp_dir.mkdir(exist_ok=True)

    # Копируем и переименовываем файлы
    for source, dest in source_images.items():
        source_path = static_dir / source
        dest_path = temp_dir / dest
        if source_path.exists():
            shutil.copy2(source_path, dest_path)
            print(f"✓ Скопирован файл: {source} → {dest}")
        else:
            print(f"✕ Не найден файл: {source}")


if __name__ == "__main__":
    copy_and_rename_images()
