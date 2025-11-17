# Руководство по реализации шага 5: будущие расширения MyWave

## 1. Общий план шага 5
1. **Цель** — превратить текущие витрины туров/челленджей в расширяемую платформу: единая JSON-LD разметка, конфиги Safari/Challenge, интеграция в AI инструменты, календарь/аналитику и RAG.
2. **Подсистемы** — маршруты Flask (`/projects`, `/events`), шаблоны + JSON-LD слой, `docs/ai_tools_site_concierge.md`, AI Gateway (регистрация новых tools), календарь/бронирования (`create_workout_if_not_exists`), аналитика (`/analytics/log`), RAG (`knowledge_base/`, SQLite индексатор).

## 2. Стандартизация JSON-LD для туров и челленджей
1. **Выделение слоя** — создайте модуль `app/seo/schema_org/` с функциями `build_event_schema(data: ShowcaseConfig)`, `build_tour_schema`, `build_challenge_schema`. Маршруты импортируют готовую структуру и сериализуют её в шаблон.
2. **Расширяемая структура** — описывайте витрины через `ShowcaseConfig`, содержащий `type`, `name`, `description`, `city`, `country`, `start_date`, `end_date`, `tags`, `price`, `capacity`, `cta`. JSON-LD функции мапят тип на подходящий `@type` (`TouristTrip`, `SportsEvent`, `EventSeries`). Тот же набор полей используйте в API/внутреннем представлении, чтобы AI-инструменты и шаблоны могли фильтровать.
3. **Фильтры** — добавьте в объект конфигурации поля `city`, `tags`, `skill_level`, `season`. JSON-LD должен включать их (через `"location": {"addressLocality": city}` и `"additionalProperty": [{"name": "tags", ...}]`).
4. **Совместимость** — старые структуры `/projects` и `/events` оборачивайте адаптером: функция `legacy_to_showcase(legacy_dict)` заполняет недостающие поля дефолтами. Плавно переводите шаблоны на новую схему, оставляя fallback на старый формат, пока не мигрируете все витрины.

## 3. Подготовка к новым витринам /projects и /events
1. **Конфигурации** — создайте директорию `configs/showcases/` с YAML/JSON файлами (`wake_surf_safari.yaml`, `sochi_camp.yaml`). Структура: `id`, `route`, `template`, `schema_type`, `content_blocks`, `gallery`, `pricing`, `faq_refs`.
2. **Фабрика витрин** — реализуйте сервис `app/services/showcases.py` с функциями `load_showcase_configs()`, `get_showcase_by_route(route)`, `render_showcase(config)`. `/projects` и `/events` превращаются в маршруты, которые просто выбирают нужный конфиг и используют шаблон (Jinja) + JSON-LD билдер.
3. **Добавление новых витрин** — чтобы выпустить новый тур/челлендж, контент-команда добавляет YAML-файл + markdown блоки (в `content/showcases/<id>/`). Код автоматически подхватывает конфиг, JSON-LD и шаблон через фабрику, без правок бизнес-логики.

## 4. Расширение инструментов AI (docs/ai_tools_site_concierge.md)
1. **Структура схем** — сгруппируйте инструменты по доменам: `showcases`, `bookings`, `leaderboards`. Для каждого инструмента опишите версионируемую схему: `"$id": "ai.tools.showcase.route.v1"`, `"version": "1.0"`.
2. **Примеры инструментов**:
   - `get_showcase_itinerary`: вход `{"showcase_id": "wake_surf_safari", "date": "2025-06-12"}`, ответ — массив этапов с локациями, активностями, ссылками.
   - `get_challenge_leaderboard`: вход `{"challenge_id": "wake_challenge_2025", "limit": 10}`, ответ — топ-участники, критерии.
   - `join_challenge`: вход `{"challenge_id", "user_contact", "experience_level"}`, результат — подтверждение + ID бронирования.
3. **Версионирование** — фиксируйте `version` в схеме и в коде AI Gateway. При изменениях добавляйте `v2`, оставляя обратную совместимость. Документируйте изменения в `docs/ai_tools_site_concierge.md`, а в коде gateway держите мапу `tool_name -> handler_vX`.

## 5. Интеграция Safari бронирования с календарём и аналитикой
1. **Календарь** — расширьте `create_workout_if_not_exists` параметрами `showcase_id`, `trip_date`, `slot_type`. При создании Safari брони вызывайте этот сервис, чтобы записать событие в Google Sheets/Calendar. Слои: `services/bookings.py` -> `integrations/google_calendar.py`.
2. **Модели** — в БД держите таблицу `safari_bookings` (`id`, `showcase_id`, `user_id`, `status`, `start_date`, `end_date`, `capacity_used`, `source`). Свяжите с `calendar_events` и `analytics_events` через FK.
3. **Аналитика** — добавьте события: `safari_booking_created`, `safari_booking_updated`, `safari_waitlist_joined`, `challenge_joined`, `challenge_score_updated`. Регистрируйте их в модуле аналитики, добавляя поля `showcase_id`, `city`, `source` (web/ai/mobile), `user_segment`. `/analytics/log` расширьте валидацию.
4. **Связка** — при успешном бронировании: a) создаём запись в таблице, b) вызываем календарь, c) логируем аналитическое событие с user_id, showcase_id, каналом. Для AI-инициированных броней добавляйте поле `origin="ai_gateway"`.

## 6. Расширение RAG и автоматическая индексация
1. **Структура knowledge_base** — добавьте папки `knowledge_base/safari/`, `knowledge_base/challenge/`, `knowledge_base/faq/`. Каждый документ содержит front-matter (YAML) с метаданными (`city`, `dates`, `difficulty`, `type`).
2. **Индексатор** — расширьте CLI (`python tools/index_knowledge_base.py --domain safari`). Скрипт читает фронт-маттер, записывает в SQLite таблицу `kb_documents` (id, type, path, metadata_json, embedding). Метаданные включают `showcase_id`, `city`, `season`, `tags`.
3. **Автообновление** — настройте pre-commit или CI шаг, который при изменении файлов в `knowledge_base/` запускает индексатор. В проде — периодический job (cron) или Celery task.
4. **Стратегия обновлений** — при добавлении новой витрины контент-команда кладёт документы в соответствующую папку, запускает `make index-kb`. Скрипт обновляет SQLite, помечая старые версии как архивные (поле `is_active`).

## 7. Архитектурные рекомендации
1. **Слои** — отделите маршруты (Flask blueprints) от сервисов (`app/services/`), интеграций (`app/integrations/`), данных (`app/models/`). JSON-LD знание держите в `app/seo/schema_org/` и инжектируйте в шаблоны.
2. **Именование** — используйте префикс `showcase_` для модулей, `ShowcaseConfig`/`ShowcaseService` для классов. Функции — глаголы (`build_showcase_schema`, `register_showcase_tools`). Папки: `services/showcases`, `integrations/calendar`, `seo/schema_org`.
3. **Расширяемость** — каждая витрина — конфиг + markdown + assets. Сервисы читают конфиг, формируют DTO, рендерят шаблон, генерируют JSON-LD, регистрируют инструменты и записи в RAG.

## 8. План миграции и внедрения
1. **Этап 1** — стандартный JSON-LD слой и конфиги витрин. Включите feature-flag `SHOWCASE_FACTORY_ENABLED` в конфиге, чтобы поэтапно подключать маршруты.
2. **Этап 2** — обновление AI-инструментов и документации (`docs/ai_tools_site_concierge.md`). Добавьте флаг `AI_SHOWCASE_TOOLS_ENABLED`.
3. **Этап 3** — интеграция бронирования в календарь и аналитику (`SAFARI_BOOKINGS_ENABLED`).
4. **Этап 4** — расширение RAG + автоиндексация (`SHOWCASE_RAG_V2`). Каждый этап деплойте отдельно, с миграциями БД и обратной совместимостью.

## 9. Тестирование и проверка результата
1. **JSON-LD** — валидируйте через Google Rich Results Test (скрипт `npm run test:structured-data`). Unit-тесты: `test_schema_org.py` проверяет содержимое `@type`, обязательные поля.
2. **AI-инструменты** — тесты JSON Schema (`pytest tests/test_ai_schemas.py`) + интеграционные вызовы AI Gateway с mock-клиентом.
3. **Бронирование/аналитика** — unit-тесты сервисов (`test_showcase_bookings.py`), smoke-тесты API (`pytest tests/test_showcase_routes.py`). Проверяйте, что события попадают в Google Sheets/Calendar (mock) и аналитический лист.
4. **RAG** — тесты индексатора (`test_kb_indexer.py`), smoke-запросы к AI с новыми документами, проверка фильтрации по `showcase_id`.

## 10. Документация для разработчиков и контент-команды
1. **Новый тур/челлендж** — добавьте гайд в `docs/showcases.md`: шаги (создать YAML, контент, JSON-LD, запустить индексатор). Обязательные поля: `name`, `city`, `dates`, `capacity`, `pricing`, `contact`.
2. **AI-инструменты** — в `docs/ai_tools_site_concierge.md` добавьте раздел «Showcase tools»: описание полей, версий, примеры запросов/ответов.
3. **Knowledge base** — обновите `docs/knowledge_base.md`: как структурировать файлы, метаданные, запуск `make index-kb`. Добавьте чек-лист для контент-команды.
