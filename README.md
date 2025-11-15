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

Контейнер собирает production-образ (Gunicorn + Nginx). После запуска UI и API доступны на `http://localhost:8080`. Redis уже проброшен как `redis://redis:6379/0`, а Postgres живёт во встроенном volume `pgdata`.

### Production-образ

- **Gunicorn** работает в `eventlet`-режиме и слушает `127.0.0.1:8000`. Конфиг (`docker/gunicorn.conf.py`) настраивается через переменные `GUNICORN_*` и `APP_MODULE`.
- **Nginx** принимает трафик на `:8080`, проксирует `/api/*` и статику, и отдаёт health-check `/healthz`, который пробрасывается в `/api/health` приложения.
- **Health-check** внутри Dockerfile проверяет `http://127.0.0.1:8080/api/health`, поэтому продовый оркестратор сразу узнает о сбое БД/Redis.
- **Логи** Nginx и Gunicorn отправляются в stdout/stderr, что упрощает сбор через Docker/Timeweb.

Для продакшн‑деплоя достаточно передать переменные окружения (`.env` или secrets) и запустить `docker build` / `docker run`.

## AI Gateway (консьерж и инструменты)

Гейтвей объединяет чат-консьержа, функции Site/Safari/Challenge и валидацию payload'ов.

- Реестр инструментов описан через JSON Schema (см. `docs/ai_tools_site_concierge.md`).
- HTTP‑контракт чата задокументирован в `docs/ai_concierge_api.md`.
- Метрики публикуются через Prometheus (`mywave_ai_concierge_requests_total`, latency, tool validation).
- Пилотная обратная связь фиксируется через `POST /api/concierge/feedback` и влияет на порядок регистрации инструментов.

### Режимы работы

| Режим | Env | Когда использовать |
| --- | --- | --- |
| Mock (по умолчанию) | `MYWAVE_AI_MODE=mock` или переменная отсутствует | Локальная разработка и CI. Используется `MockOpenAIClient`, который умеет имитировать tool-calls через строку `__call_tool__:<name>:<json>` |
| Real (OpenAI) | `MYWAVE_AI_MODE=real` + `OPENAI_API_KEY` | Продакшн/стенды, где нужен живой ответ модели. Контекст страницы/языка прокидывается в промпт, ответы инструментов возвращаются в UI |

#### Пример запуска в mock-режиме

```bash
export MYWAVE_AI_MODE=mock
flask --app app:create_app --debug run
```

#### Пример запуска в реальном режиме

```bash
export MYWAVE_AI_MODE=real
export OPENAI_API_KEY="sk-..."

flask --app app:create_app run --host=0.0.0.0 --port=5000
```

После запуска используйте `POST /api/concierge/message`:

```bash
curl -X POST http://localhost:5000/api/concierge/message \
  -H 'Content-Type: application/json' \
  -d '{"user_id": "local-dev", "message": "Покажи свободные слоты"}'
```

Ответ содержит поле `reply` и, при необходимости, структурированные результаты инструментов.

## Документация

- [AI Concierge API](docs/ai_concierge_api.md) — контракт `/api/concierge/message`, примеры ошибок и метрик.
- [AI Tools](docs/ai_tools_site_concierge.md) — поля payload/ответов для Site/Safari/Challenge инструментов и рекомендации по расширению набора.

## Тесты

```bash
pytest --cov
```

## Monitoring & Error Reporting

This project includes optional integrations to help monitor production issues.

- Sentry: set `SENTRY_DSN` in your environment to enable error forwarding to Sentry. SDK уже включён в зависимости, достаточно передать DSN и (опционально) `SENTRY_TRACES_SAMPLE_RATE`.
- Telegram alerts: provide `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` to enable sending short monitoring alerts to the configured chat. The helper used is `app.services.monitoring.send_monitoring_alert()`.
- Health endpoint: `GET /api/health` returns a JSON with checks for database, cache and (optionally) the AI gateway. Enable AI gateway quick check by setting `ENABLE_AI_HEALTH_CHECK=1`.
- Локальный обзор логов: `scripts/review_monitoring_logs.py logs/app.log --tail 10000` покажет сводку ошибок, rate-limit событий и латентности.

Sentry и Redis клиенты уже входят в базовый образ. Если переменные окружения не заданы, интеграции остаются выключенными.

## CI/CD

- Проверка стиля (`black --check`), юнит‑тестов и применимости миграций выполняется в `.github/workflows/ci.yml` на каждом push/PR.
- Автодеплой на Timeweb/VPS проходит через `.github/workflows/deploy.yml`: перед публикацией прогоняются тесты и миграции, затем приложение обновляется и перезапускается.
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
