# WakeSurf Challenge 2025 - Контент

## Структура файлов

Разместите следующие файлы в этой директории:

### Обязательные файлы:

1. **`index.md`** - Основной контент проекта в формате Markdown
   - Заголовки будут автоматически разбиты на секции по якорям из `menu.json`
   - Используйте заголовки `## О проекте`, `## Как это работает` и т.д.

2. **`meta.json`** - SEO метаданные
   ```json
   {
     "title": "WakeSurf Challenge 2025 — официальный проект",
     "description": "Описание для поисковых систем",
     "url": "https://mywavetraining.ru/projects/wakesurf-challenge-2025",
     "image": "https://mywavetraining.ru/static/images/challenge/challenge1.png",
     "site_name": "MyWave",
     "locale": "ru_RU"
   }
   ```

3. **`menu.json`** - Меню навигации и кнопки скачивания
   ```json
   {
     "anchors": [
       {"id": "about", "label": "О проекте"},
       {"id": "how", "label": "Как это работает"},
       {"id": "register", "label": "Регистрация"},
       {"id": "judging", "label": "Судейство"},
       {"id": "media", "label": "Медиа"},
       {"id": "partners", "label": "Партнёрам"},
       {"id": "final-day", "label": "Программа"},
       {"id": "webinars", "label": "Вебинары"},
       {"id": "faq", "label": "FAQ"},
       {"id": "contacts", "label": "Контакты"}
     ],
     "downloads": [
       {"label": "📄 Материалы участника", "href": "/static/docs/wsc_participant_pack.zip"},
       {"label": "📄 Материалы тренера", "href": "/static/docs/wsc_coach_pack.zip"},
       {"label": "📄 Пакет спонсора", "href": "/static/docs/wsc_sponsor_pack.zip"}
     ]
   }
   ```

4. **`sponsor_packages.json`** - Пакеты спонсоров
   ```json
   {
     "packages": [
       {
         "tier": "Бронза",
         "price": 100000,
         "deliverables": ["Логотип на сайте", "Упоминания в соцсетях"]
       }
     ],
     "currency": "₽",
     "contacts": {
       "email": "Y.Valeev@gmail.com",
       "phone": "+7 916 011 71 79"
     }
   }
   ```

5. **`judging_criteria.json`** - Критерии судейства
   ```json
   {
     "outliers": {
       "threshold": 2.0
     }
   }
   ```

6. **`schema-event.jsonld`** - JSON-LD схема для SEO
   ```json
   {
     "@context": "https://schema.org",
     "@type": "SportsEvent",
     "name": "WakeSurf Challenge 2025"
   }
   ```

## Документы для скачивания

Разместите ZIP файлы в `static/docs/`:
- `wsc_participant_pack.zip` - Материалы для участников
- `wsc_coach_pack.zip` - Материалы для тренеров
- `wsc_sponsor_pack.zip` - Пакет для спонсоров
- `final_day_program.pdf` - Программа финального дня (опционально)
- `webinar_calendar.pdf` - Календарь вебинаров (опционально)

## Автоматическое разбиение на секции

Система автоматически разбивает `index.md` на секции по заголовкам:
- Ищет заголовки с `id` атрибутом: `## О проекте {#about}`
- Или по тексту заголовка, соответствующему `label` из `menu.json`
- Каждая секция отображается в отдельном блоке с соответствующим якорем

## Fallback

Если файлы не найдены, система использует значения по умолчанию из кода.

