# Блог/Новости: фактическое состояние (as-is)

## 1) Что обнаружено

- Блог реализован отдельным blueprint в `app/routes/blog.py`, зарегистрирован в `app/__init__.py`.
- Публичные страницы:
  - `/blog` (листинг) -> `blog_index()`
  - `/blog/<slug>` (детальная) -> `blog_post(slug)`
- Есть API:
  - `/api/blog/latest`
  - `/api/blog/posts`
- Данные читаются из Google Sheets как primary source, при ошибке/пустом результате fallback в локальную БД (`app/services/blog/store.py`).
- Внутри процесса есть in-memory cache для Sheets с TTL (`BLOG_SHEETS_CACHE_TTL`).
- Markdown -> HTML + sanitize реализованы в `app/services/blog/render.py` через `markdown` + `bleach` (с allowlist и безопасными ссылками).
- Модель `BlogPost` (`app/database/models.py`) содержит поля: `title`, `slug`, `excerpt`, `content_md`, `content_html`, `content`, `cover_image_url`, `tags_json`, `status`, `published_at`, `created_at`, `updated_at`, `source_*` и др.
- На главной `templates/index.html` секция `#blog` пока статическая заглушка; последний пост туда не подставляется.
- В проекте присутствует legacy-шаблон `templates/blog.html` (категории/старый роутинг), но активными роутами блога не используется.

## 2) Почему это важно

- Есть рабочее ядро блога, но часть целевых требований уже реализована только частично.
- Несовпадение между legacy UI и текущими роутами создает риск ложных ожиданий при доработках.
- Отсутствие подключения последней новости на главной ломает целевой пользовательский сценарий.

## 3) Сверка по требованиям (✔ / ❌ / ⚠️)

### Базовая архитектура

- ✔ Блог как отдельный модуль (blueprint)
- ✔ Страницы `/blog` и `/blog/<slug>`
- ✔ Google Sheets как основной источник
- ✔ Локальная БД как fallback
- ⚠️ Локальная БД как полноценный "кэш" есть не всегда: есть fallback + отдельная sync-логика, но не единый обязательный always-on sync pipeline для фронта

### Контент и публикация

- ✔ Markdown -> HTML
- ✔ Санитайзинг HTML
- ✔ `slug`
- ✔ `excerpt`
- ✔ `cover_image` (в коде как `cover_image_url`)
- ✔ `tags` (в коде как `tags_json` + нормализованный список `tags`)
- ✔ `status` (`READY_TO_PUBLISH`/`PUBLISHED`/`published` и др.)
- ✔ `published_at`
- ✔ Пагинация
- ⚠️ На листинге фильтрация по тегу применяется к странице результатов, а не ко всей выборке до пагинации
- ❌ Вывод последнего поста на главной не реализован (хотя API есть)

### Дополнительные вопросы сверки

- categories:
  - ❌ В активной реализации нет
  - ⚠️ Есть только в неиспользуемом `templates/blog.html`
- фильтрация по тегам:
  - ✔ Есть через query `?tag=...`
- поиск по блогу:
  - ❌ Нет (нет `q`/`search` в активном роуте)

### SEO

- meta title / description:
  - ✔ Есть для листинга и поста (через блоки шаблонов + `base.html`)
- OpenGraph:
  - ✔ Есть для страницы поста
  - ⚠️ Для листинга отдельный OG-профиль не задан (используется общий из `base.html`)
- canonical:
  - ✔ Есть на странице поста (`request.url`)
  - ❌ Для `/blog` canonical не задан в HTML
  - ⚠️ В publish/writeback есть canonical URL в Sheets (`https://mywavetreaning.ru/blog/{slug}`), но это не то же самое, что canonical-тег листинга

### Админка

- ⚠️ Есть `/admin` дашборд со счетчиком постов, но нет подтвержденного UI CRUD-управления блогом
- ✔ Операционное управление публикацией сейчас в основном через Google Sheets + сервисы sync/publish

### Поля контента

- `author`:
  - ❌ Отдельного поля в `BlogPost` нет
  - ⚠️ В UI выводится `source_name` как "Источник"
- `updated_at`:
  - ✔ Есть в модели `BlogPost`

### Автоимпорт/парсер

- ✔ Импорт из parser-таблицы реализован (`fetch_parser_news_rows`, `sync_blog_from_parser_tab`)
- ⚠️ Автоматический запуск по расписанию в этом коде не закреплен явно; есть CLI/скриптовые точки запуска

### Интеграции

- Вывод последнего поста на главной:
  - ❌ Нет в текущем `templates/index.html`
  - ✔ Есть API `/api/blog/latest`, пригодный для подключения
- Связь с `events/services/projects`:
  - ❌ Прямой доменной связи в коде нет
  - ⚠️ На главной секции сосуществуют визуально, но данные независимые

## 4) Какие файлы/модули отвечают за блог

- Роуты/эндпоинты: `app/routes/blog.py`
- Регистрация blueprint: `app/__init__.py`
- Источник данных и fallback: `app/services/blog/store.py`
- Парсер-источник Sheets: `app/services/parser_news_sheet.py`
- Синхронизация Sheets -> БД: `app/services/blog/sync.py`
- Публикация + ack/writeback в Sheets: `app/services/blog/publish.py`
- Модель БД: `app/database/models.py` (`BlogPost`)
- Шаблоны:
  - `templates/blog/index.html`
  - `templates/blog/post.html`
  - `templates/index.html` (секция блога на главной)
  - `templates/base.html` (базовые SEO meta)
  - `templates/blog.html` (legacy, неактивный)

## 5) Что переносим как есть

- Текущий blueprint и маршруты `/blog`, `/blog/<slug>`.
- Гибридный доступ к данным (Sheets primary + DB fallback).
- Безопасный рендер Markdown/HTML.
- API `/api/blog/latest` и `/api/blog/posts`.

## 6) Что рефакторим в первую очередь

- Подключаем реальный "последний пост" на главной вместо заглушки.
- Добавляем поиск по блогу в активный роут и шаблон.
- Убираем неоднозначность around categories (реализовать или удалить legacy-следы).
- Унифицируем SEO для листинга (canonical + при необходимости отдельный OG-профиль).

## 7) Что откладываем

- Полноценную UI-админку для редактора блога (CRUD/workflow) — отдельным этапом.
- Глубокую доменную интеграцию блога с events/services/projects.

## 8) Риски

- Дрейф между legacy-шаблоном `templates/blog.html` и актуальными маршрутами.
- Непредсказуемость UX на главной из-за отсутствия реального latest-post блока.
- Частичное расхождение SEO-поведения между `/blog` и `/blog/<slug>`.

## 9) Критерий готовности сверки

- Сверка зафиксирована документом с отметками `✔/❌/⚠️`.
- Для каждого спорного пункта указано фактическое место в коде.
- Подготовлен отдельный backlog blog-only до целевого уровня.
