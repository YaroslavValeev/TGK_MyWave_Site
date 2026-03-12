# Запуск проекта и тестов

Краткая инструкция для локальной разработки и стенда.

---

## 1. Запуск проекта локально

```bash
# Установка зависимостей
pip install -r requirements.txt

# Опционально: переменные окружения
cp .env.example .env   # если есть
# или задайте в .env: SECRET_KEY, OPENAI_API_KEY, SPREADSHEET_ID, GOOGLE_* и т.д.

# Запуск
python main.py
```

Приложение будет доступно на `http://127.0.0.1:5000` (или следующий свободный порт 5001–5010).

---

## 2. Тесты без Google-сервисов

По умолчанию тесты **не обращаются** к реальным Google Sheets и Calendar.

```bash
# Unit и integration тесты (без внешних сервисов)
pytest tests/unit tests/integration -v

# Smoke-тесты (без Google)
pytest tests/smoke/ -v

# Всё вместе
pytest tests/ -v --ignore=tests/e2e
```

В testing-режиме:
- `SPREADSHEET_ID` пустой — booking API использует локальную БД
- `ENABLE_GOOGLE_SERVICES=0` — инициализация Google отключена
- Integration conftest подменяет вызовы Google Sheets/Calendar

---

## 3. E2E тесты (Playwright)

E2E проверяют критический путь в браузере. Не требуют Google.

```bash
# Установить браузеры Playwright (один раз)
playwright install

# Запуск E2E
pytest tests/e2e/ -v
```

E2E поднимают локальный сервер с моками для calendar/sheets.

---

## 4. Обязательные env-переменные

| Переменная | Когда нужна |
|------------|-------------|
| `SECRET_KEY` | Всегда (production) |
| `OPENAI_API_KEY` | Чат |
| `SPREADSHEET_ID` | Бронирование (Sheets) |
| `GOOGLE_CALENDAR_ID` | События в календаре |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Доступ к Sheets/Calendar |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Админка |
| `REDIS_URL` | SocketIO (опционально) |
| `DATABASE_URL` | Production БД |

Для локальной разработки достаточно `SECRET_KEY` и `OPENAI_API_KEY`.

---

## 5. Как понять, что стенд поднят корректно

1. `curl http://localhost:5000/health` — 200, `"status": "ok"`
2. Главная страница открывается: `http://localhost:5000/`
3. Чат открывается и отправляет сообщение
4. Бронирование: кнопка «Записаться» → дата → слот → форма → успех
5. `/admin/` открывается без 500

---

## 6. CI

В CI рекомендуется:

- `ENABLE_GOOGLE_SERVICES=0`
- `pytest tests/ -v --ignore=tests/e2e` (E2E можно запускать отдельно при необходимости)
