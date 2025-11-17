# Руководство по витринам Safari/Challenge

Этот документ описывает процесс добавления нового тура или челленджа на страницы `/projects` и `/events`, а также интеграцию с AI-инструментами, аналитикой и RAG.

## 1. Конфигурация витрины
1. Создайте файл `configs/showcases/<slug>.yaml`.
2. Обязательные поля: `id`, `slug`, `name`, `summary`, `description`, `category`, `kind`, `schema_type`, `status`, `city`, `country`, `start_date`, `end_date`.
3. Рекомендуемые поля: `tags`, `level`, `price_from`, `capacity`, `cover_image`, `gallery`, `cta_url`, `channels`, `metadata`, `itinerary`, `leaderboard`.
4. Поле `channels` определяет, где показывать витрину (`projects`, `events`).
5. После сохранения файла перезапустите приложение или очистите кэш `app.services.showcases.load_showcase_configs.cache_clear()`.

## 2. Рендеринг и JSON-LD
1. Роуты `/projects` и `/events` используют сервис `app/services/showcases.py` и автоматически добавят новую витрину в грид и JSON-LD.
2. JSON-LD генерирует модуль `app/seo/schema_org.py`. Следите за корректностью дат и картинок.

## 3. AI-инструменты
1. Для сценариев AI добавляйте схемы в `app/ai/tools_schema.py` и описание в `docs/ai_tools_site_concierge.md`.
2. Функции `get_showcase_itinerary`, `get_challenge_leaderboard`, `join_challenge` читают данные из конфигов и пишут аналитику.
3. При изменении формата создавайте новую версию схемы (`...v2`).

## 4. Бронирования и аналитика
1. Используйте `create_showcase_booking` при необходимости привязать Safari к календарю (`create_workout_if_not_exists`).
2. Аналитика пишет события `safari_booking_created` и `challenge_joined` через `log_analytics_event`.
3. Для кастомных каналов передавайте `channel` и `showcase_id` в `/analytics/log`.

## 5. Knowledge Base / RAG
1. Документы лежат в `knowledge_base/safari/` и `knowledge_base/challenge/` с YAML front-matter.
2. После изменения данных запустите `python tools/index_knowledge_base.py --domain safari` (или `challenge`).
3. Таблица `kb_documents` в `knowledge_base.db` хранит метаданные (`showcase_id`, `city`, `season`).

## 6. Проверка
1. Прогоните `pytest tests/unit/test_showcases.py`.
2. Валидируйте JSON-LD через `npm run test:structured-data` (если доступно) или `tools/validate_with_schema_org.py`.
3. Убедитесь, что AI-инструменты доступны через `/api/ai/gateway/tools` (если роут включен).
