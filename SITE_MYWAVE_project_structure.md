# Структура проекта Site_MyWave

## Точка входа

- `wsgi.py` — WSGI entrypoint для Gunicorn/WSGI-серверов
- `main.py` — основной запуск приложения (Flask)

## Docker

- `Dockerfile` — сборка продакшн-образа
- `docker-compose.yml` — локальный и продакшн-стек (web + db)

## CI/CD

- `.github/workflows/deploy.yml` — автоматизация сборки и деплоя через GitHub Actions

## Основные директории и файлы

- `app/` — приложение Flask
  - `routes/` — маршруты (в том числе `api.py`)
  - `forms/` — формы (WTForms)
  - `services/` — бизнес-логика, интеграции
  - `database/` — модели SQLAlchemy
  - `templates/` — HTML-шаблоны
  - `static/` — статика
- `configs/service_account.json` — сервисный аккаунт Google
- `requirements.txt` — зависимости
- `.env`, `.env.sample` — переменные окружения

## Новые файлы

- `app/forms/*.py` — формы
- `app/routes/api.py` — REST API
- `wsgi.py` — WSGI entrypoint
