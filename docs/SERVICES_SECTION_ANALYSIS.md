# Раздел «Услуги» — Анализ и план улучшений

## 1. Файлы, задействованные в разделе

### Backend
| Файл | Роль |
|------|------|
| `app/routes/services.py` | Роуты `/services/`, маппинг `_SERVICES_RAW`, вызов `resolve_card_images` |
| `app/services/images_resolver.py` | Скан папок, формирование `images[]`, `cover`, `fallback` |

### Frontend — шаблоны
| Файл | Роль |
|------|------|
| `templates/services.html` | Страница услуг: карусель карточек, изображения, модалки |
| `templates/partials/booking_modals.html` | Модалки: modalCalendar, modalCamp, modalCoachTriper, modalConsulting |
| `templates/base.html` | Подключение CSS/JS, хедер с ссылкой на Услуги |

### Frontend — стили
| Файл | Роль |
|------|------|
| `static/css/services-carousel.css` | Стили карусели, карточек, inner carousel |
| `static/css/image-effects.css` | Плейсхолдеры, анимации, fallback для `.service-image` |
| `static/css/modals.css` | Стили модальных окон |
| `static/css/style.css` | Общие стили |

### Frontend — скрипты
| Файл | Роль |
|------|------|
| `static/js/carousel-arrows.js` | Стрелки карусели (prev/next) |
| `static/js/services-expand.js` | Раскрытие карточек по клику |
| `static/js/card-gallery.js` | Переключение изображений внутри карточки (2+ фото) |
| `static/js/image-effects.js` | Lazy load, placeholder, fallback при ошибке |
| `static/js/image-fallback.js` | Глобальный fallback для `img[data-fallback]` |
| `static/js/booking.js` | Открытие модалок, выбор даты/слота, отправка формы |
| `static/js/modal-lead-forms.js` | Формы Camp/CoachTriper/Consulting |

### Медиа — папки и маппинг
| Папка | Карточка | Файлы |
|-------|----------|-------|
| `static/images/Services/Gym/` | «Запись на тренировку (Зал)» | balance.jpg, training1.jpg |
| `static/images/Services/Boat/` | «Запись на катер» | boat-01.jpg, boat-02.jpg |
| `static/images/Services/Camp/` | «Camp» | camp-01.jpg, camp-02.jpg |
| `static/images/Services/CoachTriper/` | «CoachTriper» | coach-01.jpg, coach-02.jpg |
| `static/images/Services/Consulting/` | «Consulting» | cons-01.JPG, cons-02.JPG |

### Вспомогательные
| Файл | Роль |
|------|------|
| `scripts/seed_service_images.py` | Сид БД для `Image` с group='services' — **НЕ используется** на странице услуг (страница берёт картинки из папок через `images_resolver`) |
| `app/services/showcases.py` | Логика проектов/ивентов; `_ensure_images_resolved` — для проектов, не для услуг |

---

## 2. Текущий маппинг медиа (откуда берутся иллюстрации)

Источник — **сканирование папок** через `images_resolver.resolve_card_images()`:

```python
# app/routes/services.py (строки 94–102)
_SERVICES_RAW = [
    {'image_folder': 'images/Services/Gym', ...},       # → Зал
    {'image_folder': 'images/Services/Boat', ...},      # → Катер
    {'image_folder': 'images/Services/Camp', ...},      # → Camp
    {'image_folder': 'images/Services/CoachTriper', ...}, # → CoachTriper
    {'image_folder': 'images/Services/Consalting', ...},  # → Consulting (папка с опечаткой!)
]
```

Резолвер:
- Сканирует `static/{image_folder}/`
- Возвращает `{images, cover, fallback}` — `cover` = первый файл, fallback = `images/Place1Logo.png`

---

## 3. Проблемы и расхождения

### 3.1 Иллюстрации не отображаются или отображаются неверно

| Проблема | Причина | Решение |
|----------|---------|---------|
| Картинки не показываются | Возможна ошибка пути на Windows (регистр, слэши) | Проверить, что `resolve_card_images` возвращает валидные пути; логировать при resolve |
| Конфликт `image-effects.js` | Начальная `opacity: 0` — картинки могут «мигать» или не показываться до load | Убедиться, что `img.complete` корректно обрабатывается; fallback на `images/Place1Logo.png` |
| `card-gallery.js` формирует URL | `baseUrl + path` = `origin + '/static/' + path` — при reverse proxy/подкаталоге может ломаться | Использовать `url_for` на бэкенде и передавать полные URL или data-атрибут с base |

### 3.2 Опечатка в имени папки

- Папка: `Consalting` (опечатка)
- Карточка: «Consulting»
- В `_SERVICES_RAW` указано `images/Services/Consalting` — маппинг корректен, но имя папки лучше переименовать в `Consulting` для единообразия.

### 3.3 Два разных carousel-скрипта

- `services-carousel.js` — ищет `.js-service-carousel`, `.service-card-media-img` — **не используется** в `services.html`
- `card-gallery.js` — ищет `.card-media-carousel`, `.service-image` — **используется**
- Рекомендация: удалить или переиспользовать `services-carousel.js`, чтобы не путать.

### 3.4 Fallback-цепочка

- Основной: `images/Place1Logo.png` ✅ (есть)
- Запасной при отсутствии Place1Logo: `images/wake_challenge.jpg` ✅ (есть)

---

## 4. Рекомендации по улучшению

### 4.1 Исправить маппинг и документировать его

- [ ] Переименовать папку `Consalting` → `Consulting` и обновить `image_folder` в `_SERVICES_RAW`
- [ ] Либо оставить `Consalting` и добавить комментарий о намеренной совместимости со старыми путями

### 4.2 Упростить и унифицировать скрипты изображений

- [ ] Убрать дублирование: `image-effects.js` + `image-fallback.js` — объединить логику или чётко разграничить роли
- [ ] Удалить или переписать `services-carousel.js` под фактическую разметку (`.card-media-carousel`)

### 4.3 Использовать `url_for` для путей в data-атрибутах

Сейчас в `data-images` передаются относительные пути, а `card-gallery.js` склеивает их с `origin + '/static/'`. Лучше на бэкенде формировать полные URL или путь относительно static:

```html
data-images="{{ service.images|map('static_path')|join(',') }}"
```

и в JS использовать готовые URL.

### 4.4 Добавить проверку при старте

- [ ] При загрузке страницы `/services/` — убедиться, что для каждой карточки `resolve_card_images` возвращает непустой `images`
- [ ] Логировать предупреждение, если папка пуста или не найдена

### 4.5 Централизовать конфиг маппинга

Вынести маппинг «папка → карточка» в YAML/JSON (аналогично `configs/showcases/`), чтобы:
- Легко добавлять новые услуги
- Избежать опечаток в путях
- Документировать ожидаемую структуру папок

---

## 5. Итоговая сводка маппинга (как должно быть)

| Карточка | service_id | Папка | Fallback |
|----------|------------|-------|----------|
| Зал | gym | `static/images/Services/Gym/` | Place1Logo.png |
| Катер | boat | `static/images/Services/Boat/` | Place1Logo.png |
| Camp | camp | `static/images/Services/Camp/` | Place1Logo.png |
| CoachTriper | coach_triper | `static/images/Services/CoachTriper/` | Place1Logo.png |
| Consulting | consulting | `static/images/Services/Consalting/` *(или Consulting/)* | Place1Logo.png |

---

*Документ создан автоматически по запросу пользователя.*
