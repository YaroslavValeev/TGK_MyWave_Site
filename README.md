# MyWave

## Быстрый старт

```bash
git clone <repo_url>
cd Site_MyWave
git checkout main
cp .env.sample .env
```

## Локальный запуск через Docker

```bash
docker-compose up --build
```

## Тесты

```bash
pytest --cov
```

## CI/CD

- Сборка и деплой через GitHub Actions (см. `.github/workflows/deploy.yml`).
- Dockerfile и docker-compose для продакшн и локального запуска.

## ER-диаграмма

### User

- id (PK)
- username, email, password_hash, is_admin, role
- Связи:
  - bookings: One-to-Many → Booking (user_id)
  - workouts: One-to-Many → Workout (user_id)

### Booking

- id (PK)
- name, phone, date, time, created_at, status
- user_id (FK) → User.id
- event_id (FK) → CalendarEvent.id

### CalendarEvent

- id (PK)
- event_id (уникальный), summary, start, end, created_at
- Связи:
  - bookings: One-to-Many → Booking (event_id)

### Contact

- id (PK)
- name, email, message, created_at

### BlogPost

- id (PK)
- title, teaser, content, slug, created_at
- Связи:
  - chat_messages: One-to-Many → ChatMessage (blog_post_id)

### ChatMessage

- id (PK)
- user, message, created_at
- blog_post_id (FK) → BlogPost.id

### Review

- id (PK)
- name, rating, text, created_at

### Assistant

- id (PK)
- assistant_id (уникальный), name, instructions, model, created_at, updated_at

### Workout

- id (PK)
- user_id (FK) → User.id
- date, time, duration, type, notes, created_at

### Analytics

- id (PK)
- metric, value

#### Связи между таблицами

- User 1—* Booking (user_id)
- User 1—* Workout (user_id)
- CalendarEvent 1—* Booking (event_id)
- BlogPost 1—* ChatMessage (blog_post_id)

Остальные таблицы (Contact, Review, Assistant, Analytics) — самостоятельные, без внешних ключей.

## Swagger/OpenAPI

Документация REST API доступна по адресу: `/swagger/` (Flask-RESTX).

## Настройка сервисного аккаунта Google

Для работы с Google API (Sheets, Calendar, Drive) необходимо настроить сервисный аккаунт:

1. Создайте сервисный аккаунт в Google Cloud Console
2. Скачайте JSON-файл с учетными данными
3. Разместите файл в одном из следующих мест:
   - `instance/service_account.json` (рекомендуется)
   - Вне проекта (укажите полный путь в переменной окружения `GOOGLE_SERVICE_ACCOUNT_FILE`)

### Важно

- Не коммитьте файл сервисного аккаунта в репозиторий
- Храните файл в безопасном месте
- Используйте разные сервисные аккаунты для разработки и продакшена

## Установка и запуск

1. Создайте виртуальное окружение:

```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
venv\Scripts\activate     # для Windows
```

2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Создайте файл `.env` на основе `.env.sample`:

```bash
cp .env.sample .env
```

4. Заполните необходимые переменные окружения в `.env`

5. Запустите приложение:

```bash
python app.py
```

## Структура проекта (основное)

- `app/` - основной код приложения
- `instance/` - конфигурационные файлы (не коммитятся)
- `templates/` - HTML шаблоны
- `static/` - статические файлы (CSS, JS, изображения)
- `.env` - переменные окружения (не коммитится)
- `.env.sample` - шаблон для `.env`
