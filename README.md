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

## Monitoring & Error Reporting

This project includes optional integrations to help monitor production issues.

- Sentry: set `SENTRY_DSN` in your environment to enable error forwarding to Sentry. Adjust `SENTRY_TRACES_SAMPLE_RATE` for performance tracing (defaults to 0.1).
- Telegram alerts: provide `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` to enable sending short monitoring alerts to the configured chat. The helper used is `app.services.monitoring.send_monitoring_alert()`.
- Health endpoint: `GET /api/health` returns a JSON with checks for database, cache and (optionally) the AI gateway. Enable AI gateway quick check by setting `ENABLE_AI_HEALTH_CHECK=1`.

The Sentry SDK is optional at runtime; the app will start even if `sentry-sdk` is not installed. To enable Sentry in production, add `sentry-sdk` to `requirements.txt` and provide a valid `SENTRY_DSN`.

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
