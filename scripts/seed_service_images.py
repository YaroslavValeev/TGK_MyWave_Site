#!/usr/bin/env python3
"""
Скрипт для заполнения таблицы Image записями с group='services'.
Эти изображения будут использоваться в системе рекомендаций.

Использование:
    python scripts/seed_service_images.py

Создаёт 10 тестовых записей с различными типами услуг.
"""
import sys
import os

# Добавляем родительскую директорию в PYTHONPATH для импорта app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.database.models import db, Image
from datetime import datetime


SERVICE_IMAGES = [
    {
        "filename": "service-training-1.webp",
        "orig_filename": "Тренировка 1",
        "mime_type": "image/webp",
        "size": 45000,
        "width": 800,
        "height": 600,
        "title": "Тренировка на тренажёрах",
        "alt": "Профессиональные тренировки по вейксерфингу",
        "caption": "Авторская методика обучения с высоким результатом",
        "group": "services",
        "order": 1,
        "format": "webp"
    },
    {
        "filename": "service-training-2.webp",
        "orig_filename": "Тренировка 2",
        "mime_type": "image/webp",
        "size": 48000,
        "width": 800,
        "height": 600,
        "title": "Индивидуальные занятия",
        "alt": "Персональные тренировки с инструктором",
        "caption": "Гибкий график, максимум внимания тренера",
        "group": "services",
        "order": 2,
        "format": "webp"
    },
    {
        "filename": "service-boat-1.webp",
        "orig_filename": "Катер 1",
        "mime_type": "image/webp",
        "size": 52000,
        "width": 800,
        "height": 600,
        "title": "Тренировка за катером",
        "alt": "Вейксерфинг на волне за катером",
        "caption": "Профессиональное оборудование и безопасность",
        "group": "services",
        "order": 3,
        "format": "webp"
    },
    {
        "filename": "service-wake-discovery-1.webp",
        "orig_filename": "Wake Discovery",
        "mime_type": "image/webp",
        "size": 41000,
        "width": 800,
        "height": 600,
        "title": "Wake Discovery (ознакомление)",
        "alt": "Вводное занятие для новичков",
        "caption": "Идеальный старт для начинающих райдеров",
        "group": "services",
        "order": 4,
        "format": "webp"
    },
    {
        "filename": "service-camp-1.webp",
        "orig_filename": "Wake Camp",
        "mime_type": "image/webp",
        "size": 55000,
        "width": 800,
        "height": 600,
        "title": "Wake Camp (интенсив)",
        "alt": "Интенсивный лагерь для совершенствования",
        "caption": "Недельная прокачка техники и физподготовки",
        "group": "services",
        "order": 5,
        "format": "webp"
    },
    {
        "filename": "service-group-lesson.webp",
        "orig_filename": "Групповой урок",
        "mime_type": "image/webp",
        "size": 44000,
        "width": 800,
        "height": 600,
        "title": "Групповые занятия",
        "alt": "Обучение в дружеской атмосфере",
        "caption": "Энергия группы + профессиональный подход",
        "group": "services",
        "order": 6,
        "format": "webp"
    },
    {
        "filename": "service-advanced.webp",
        "orig_filename": "Продвинутый уровень",
        "mime_type": "image/webp",
        "size": 50000,
        "width": 800,
        "height": 600,
        "title": "Программа для продвинутых",
        "alt": "Совершенствование трюков и техники",
        "caption": "Для опытных райдеров готовых к новым вызовам",
        "group": "services",
        "order": 7,
        "format": "webp"
    },
    {
        "filename": "service-kids.webp",
        "orig_filename": "Детские занятия",
        "mime_type": "image/webp",
        "size": 39000,
        "width": 800,
        "height": 600,
        "title": "Детская школа вейксерфинга",
        "alt": "Безопасное обучение для детей 8+",
        "caption": "Веселье, спорт и развитие координации",
        "group": "services",
        "order": 8,
        "format": "webp"
    },
    {
        "filename": "service-fitness.webp",
        "orig_filename": "Фитнес",
        "mime_type": "image/webp",
        "size": 46000,
        "width": 800,
        "height": 600,
        "title": "Спортивный фитнес",
        "alt": "Специализированная подготовка спортсмена",
        "caption": "Укрепляем нужные группы мышц для вейка",
        "group": "services",
        "order": 9,
        "format": "webp"
    },
    {
        "filename": "service-consultation.webp",
        "orig_filename": "Консультация",
        "mime_type": "image/webp",
        "size": 38000,
        "width": 800,
        "height": 600,
        "title": "Консультация тренера",
        "alt": "Персональная консультация и план обучения",
        "caption": "Анализ уровня + создание плана развития",
        "group": "services",
        "order": 10,
        "format": "webp"
    }
]


def seed_service_images():
    """Добавляет тестовые изображения услуг в БД."""
    app = create_app()
    
    with app.app_context():
        try:
            # Проверяем, не добавлены ли уже
            existing = Image.query.filter_by(group='services').count()
            if existing > 0:
                print(f"⚠️  В БД уже содержится {existing} изображений с group='services'")
                response = input("Продолжить добавление? (y/n): ")
                if response.lower() != 'y':
                    print("Отменено.")
                    return 1
            
            print(f"📸 Добавление {len(SERVICE_IMAGES)} изображений услуг...\n")
            
            for data in SERVICE_IMAGES:
                img = Image(
                    filename=data["filename"],
                    orig_filename=data["orig_filename"],
                    mime_type=data["mime_type"],
                    size=data["size"],
                    width=data["width"],
                    height=data["height"],
                    title=data["title"],
                    alt=data["alt"],
                    caption=data["caption"],
                    group=data["group"],
                    order=data["order"],
                    format=data["format"],
                    optimized=False
                )
                db.session.add(img)
                print(f"   ✓ {data['title']} (order={data['order']})")
            
            db.session.commit()
            print(f"\n✅ Успешно добавлено {len(SERVICE_IMAGES)} изображений!")
            
            # Проверка
            total = Image.query.filter_by(group='services').count()
            print(f"📊 Всего в group='services': {total} записей")
            
            return 0
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Ошибка при добавлении: {str(e)}")
            import traceback
            traceback.print_exc()
            return 1


if __name__ == "__main__":
    sys.exit(seed_service_images())
