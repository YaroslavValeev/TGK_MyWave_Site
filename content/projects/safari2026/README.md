# Wake Surf Safari 2026 - Контент

## Структура файлов

Разместите следующие файлы в этой директории:

### Обязательные файлы:

1. **`index.md`** - Основной контент проекта в формате Markdown
   - Будет автоматически конвертирован в HTML
   - Используйте стандартный Markdown синтаксис

2. **`meta.json`** - SEO метаданные
   ```json
   {
     "title": "Wake Surf Safari 2026",
     "description": "Экспедиционный вейксерф-тур по Волге",
     "og": {
       "type": "website",
       "title": "Wake Surf Safari 2026",
       "description": "Экспедиционный вейксерф-тур по Волге",
       "image": "https://mywavetraining.ru/static/images/safari/hero.jpg",
       "url": "https://mywavetraining.ru/projects/wakesurf-safari"
     },
     "twitter": {
       "card": "summary_large_image",
       "title": "Wake Surf Safari 2026",
       "description": "Экспедиционный вейксерф-тур по Волге",
       "image": "https://mywavetraining.ru/static/images/safari/hero.jpg"
     }
   }
   ```

3. **`menu.json`** - Меню навигации (массив объектов)
   ```json
   [
     {"title": "О проекте", "href": "#content"},
     {"title": "Маршрут", "href": "#route"},
     {"title": "Партнёрам", "href": "#for-partners"},
     {"title": "Записаться", "href": "#join", "cta": true}
   ]
   ```

4. **`partner_packages.json`** - Пакеты партнёров
   ```json
   {
     "packages": [
       {
         "name": "Базовый",
         "price": 50000,
         "currency": "₽",
         "benefits": ["Логотип на сайте", "Упоминание в соцсетях"]
       }
     ],
     "contact": {
       "email": "Y.Valeev@gmail.com",
       "phone": "+7 916 011 71 79"
     }
   }
   ```

5. **`schema-event.jsonld`** - JSON-LD схема для SEO
   ```json
   {
     "@context": "https://schema.org",
     "@type": "SportsEvent",
     "name": "Wake Surf Safari 2026",
     "startDate": "2026-07-10",
     "endDate": "2026-07-18"
   }
   ```

6. **`forms.yaml`** - Конфигурация форм (опционально, для будущей генерации)
   ```yaml
   participant:
     fields:
       - name: full_name
         label: ФИО
         required: true
   ```

## Fallback

Если файлы не найдены, система использует значения по умолчанию из кода, страница будет работать.

## API Endpoints

- `POST /api/safari/participant` - Регистрация участника
- `POST /api/safari/partner` - Регистрация партнёра

Все формы защищены CSRF токенами и rate limiting (5 запросов/минуту).

