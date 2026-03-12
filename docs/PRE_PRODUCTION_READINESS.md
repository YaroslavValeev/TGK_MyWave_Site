# Pre-production readiness (Sprint 3)

## Готово к стенду

| Компонент | Статус |
|-----------|--------|
| Запуск приложения | `python main.py` или gunicorn |
| Статика | Обслуживается Flask |
| Health endpoints | `/health`, `/metrics/health` |
| Чат (WebSocket) | SocketIO + `/chat/api` |
| Бронирование | `/api/calendar/book` с защитой от дублей |
| Админка /admin/ | Открывается без 500 |
| Тесты без Google | Smoke, integration — изолированы |

## Оставшиеся блокеры для pre-production

| Блокер | Описание |
|--------|----------|
| login_manager в тестах | `/admin/images/` падает с 500 при E2E из-за отсутствия login_manager в тестовом приложении |
| Health 503 | В минимальном окружении health может возвращать 503 (Redis, cache) — не критично для старта |
| E2E browser | Тесты с Playwright (chat, booking) могут требовать headed-режим или настройку окружения |

## Рекомендации для Sprint 4

- Инициализировать Flask-Login в testing-конфиге для admin
- Добавить опциональные проверки health (Redis/cache — non-fatal)
- Документировать требования к E2E (playwright install, порты)
