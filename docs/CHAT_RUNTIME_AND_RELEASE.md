# Раздел «Чат»: production runtime и legacy

## Канонический entrypoint

- **Прод и стенд:** запуск приложения через **`main.py`** (Socket.IO + eventlet monkey_patch, затем `create_app()`).
- **WSGI:** обёртка поверх того же приложения, что создаётся в `main.py` / `app.create_app` — не через отдельный «легаси» чат-сервер.

Клиент чата ходит только в:

- `GET /chat/` — лендинг с тем же виджетом из `base.html`
- `POST /chat/api` — единственный канонический API текста и сценария брони

## Legacy (не использовать как production path для чата)

| Артефакт | Роль |
| ---------- | ------ |
| `app.py` | Альтернативная точка входа; для чата **не** считать каноном. |
| `websocket_handler.py` | Не подключается из `main.py` для основного runtime; риск дублирования обработчиков при ручном импорте. |
| `server.js` / отдельный Node-чат | Optional compatibility path на `127.0.0.1:5001`; не считать каноническим runtime для основного веб-чата. |
| `POST /api/chat` | Совместимость/прокси к тому же handler, что `/chat/api`; предпочтительно клиенту использовать `/chat/api`. |

## Persistence

- Модель и миграция: `ChatMessage`, revision с `chat_message` (см. `migrations/versions/`).
- На стенде после деплоя: `flask db upgrade` (или `alembic upgrade head` в вашем процессе).
- Проверка: `python scripts/chat_persistence_check.py` с конфигом/БД окружения стенда.

## E2E

- **HTTP-smoke (по умолчанию):** `tests/e2e/test_chat_section_http.py` — `GET /chat/`, разметка виджета.
- **Playwright:** `tests/e2e/test_chat_section.py` и `test_critical_paths.test_chat_opens_and_sends_message` — только при **`E2E_PLAYWRIGHT=1`** (иначе skip): на части окружений `live_server` + eventlet + Chromium дают таймауты.

### Ручной browser smoke (релиз)

1. Открыть `https://<стенд>/chat/` — виджет открывается (или кнопка в углу).
2. Приветствие один раз (очистить `localStorage` ключ `mw_chat_welcome_v1` для повторной проверки).
3. Обычный вопрос → ответ 200, текст в пузыре.
4. «Хочу записаться завтра» → сценарий брони (дата/слоты/подсказки).
5. Смоделировать 429 (41+ запросов с одного IP за минуту или временно снизить лимит) — дружелюбное сообщение.
6. Отключить ключ OpenAI / сломать сеть → `status: error`, текст без 500 в UI.
7. Консоль (F12): нет необработанных ошибок, блокирующих отправку.

## Persistence на стенде

1. На сервере с тем же `DATABASE_URL`, что у приложения: **`flask db upgrade`** (или `alembic upgrade head`).
2. Проверка: **`python scripts/chat_persistence_check.py`** (опционально `--config production` / переменные окружения как у приложения).
3. Доказательство записи: после одного диалога в чате — `SELECT COUNT(*) FROM chat_message;` (или скрипт с `--expect-rows 2` после пары реплик).

Если в логах **`no such table: chat_message`** — миграции не применены к этой БД.

---

## Источник системной роли (Owner: выбор политики)

| Фактическая логика | Где задаётся |
| -------------------- | ---------------- |
| **Chat Completions** | `CHAT_SYSTEM_PROMPT` в конфиге / env; файл `app/config/assistant_prompt.md` подставляется через `setdefault`, если env не задал строку. |
| **Responses API** | При `CHAT_BACKEND=responses` основной public text chat идёт через `client.responses.create(...)` с тем же `CHAT_SYSTEM_PROMPT`, history и user-friendly error mapping. |
| **Assistant API** | Только если задан `ASSISTANT_ID` и `CHAT_BACKEND` не форсирует completions. Инструкции и tools — в кабинете OpenAI для этого assistant, **не** из `assistant_prompt.md`. |
| **Fallback** | При `CHAT_BACKEND=auto`, если Assistant не вернул текст → один запрос **Chat Completions** с тем же `CHAT_SYSTEM_PROMPT` и историей. |

### Варианты для Owner

| Вариант | Плюсы | Минусы | Релиз |
| --------- | -------- | -------- | -------- |
| **A — оставить ASSISTANT_ID** | Единый «умный» ассистент в OpenAI, RAG/tools в кабинете. | Роль сайта живёт в OpenAI; нужно вручную синхронизировать с брендом MyWave. | Безопасно, если инструкции в кабинете актуальны. |
| **B — убрать ASSISTANT_ID для сайта** | Роль полностью из репозитория (`assistant_prompt.md` + env). | Нет нативных tools Assistant без отдельной интеграции. | Проще поддерживать текст роли в Git. |
| **C — `CHAT_BACKEND`** | `completions` — стабильный rollback; `responses` — controlled migration на новую OpenAI API; `assistant_only` — отладка Assistant без смешения с completions. | Нужна дисциплина env на стендах. | **Рекомендуется как переключатель** наряду с A или B. |

**Рекомендация:** для предсказуемого релиза держать **`CHAT_BACKEND=completions`** как rollback. Для controlled migration включать **`CHAT_BACKEND=responses`** на стенде и сравнивать качество/стоимость. Legacy `auto` и `assistant_only` оставлены для совместимости, но не являются целевым направлением развития.

Переменные: `CHAT_BACKEND`, `ASSISTANT_ID`, `CHAT_SYSTEM_PROMPT` (см. `.env.example`).

---

## Логи (Windows local/dev)

- Файловый вывод настраивается в **`app/modules/logger.py`**: один handler на **`logging.root`**, без множественных `TimedRotatingFileHandler` на один и тот же файл.
- **По умолчанию на Windows** — `FileHandler` **без** rollover (нет `WinError 32` при rename).
- **Linux / при необходимости** — суточная ротация; принудительно: `LOG_USE_TIMED_ROTATION=1`; отключить ротацию везде: `LOG_USE_TIMED_ROTATION=0`.

---

## Flask-Limiter (production)

- Задаётся **`RATELIMIT_STORAGE_URI`**: по умолчанию **`memory://`** (явно, без предупреждения библиотеки о «no storage»).
- **Production (несколько воркеров):** `RATELIMIT_STORAGE_URI=redis://127.0.0.1:6379/0` (или ваш Redis/Valkey). При `FLASK_ENV=production` и `memory://` в лог пишется **warning**.
- Зависимость `redis` уже в `requirements.txt`; при недоступном Redis приложение при старте может упасть — проверять connectivity на стенде.

---

## Socket.IO: два «Server initialized for eventlet»

- Ожидаемо при текущем **`main.py`**: после `create_app()` вызывается второй `socketio.init_app(..., async_mode='eventlet')`.
- Это **не дубль middleware** в смысле двух независимых серверов, а повторная привязка к тому же экземпляру `socketio` из `app.extensions`. На релиз не блокирует; убрать дубль можно отдельным рефакторингом entrypoint (P2).

---

## Извлечение ответа Assistant и thread

- Сначала `messages.list(run_id=текущий_run)` — ответ только от этого run.
- Если пусто: проход по сообщениям с полем `run_id` на объекте сообщения.
- Запасной вариант: последний по времени `assistant` с `created_at` строго после user-сообщения этого хода (не «любой последний assistant в thread»).

Журнал Google Sheets: при успехе Assistant вызывается тот же `log_dialog`, что и для Chat Completions (отключается: `CHAT_SHEETS_LOG_ASSISTANT=0`).

## Отладка ветки Assistant (`app/services/openai_service.py`)

Структурированные строки лога с префиксом **`[chat-assistant]`**:

- `phase=start` — `assistant_id`, `thread_id`, `run_id`
- `phase=run_done` — `final_status`, `last_error`
- `phase=extract_ok` / `phase=extract_fail` — длина текста, причина
- `path=fallback_completions` — при пустом ответе Assistant в режиме `auto`
- `path=completions_only` — при `CHAT_BACKEND=completions`
- `path=responses_only` — при `CHAT_BACKEND=responses`

---

## Приёмочный smoke (только чат)

| Сценарий | Результат | pass/fail | Комментарий |
| ---------- | ----------- | ----------- | ------------- |
| `GET /chat` | 200, виджет | ☐ | |
| `GET /chat/` | 200 | ☐ | |
| Виджет открывается | UI | ☐ | |
| Обычный вопрос | Содержательный ответ, не заглушка | ☐ | См. логи `[chat-assistant]` |
| Booking-intent («хочу записаться…») | Сценарий брони | ☐ | |
| Консоль браузера | Нет blocker-ошибок | ☐ | |
| `POST /chat/api` | 200, JSON с полем ответа | ☐ | |
| `chat_message` | user + assistant с полезным текстом | ☐ | После миграций |

## Owner rollout для Responses API

1. На стенде выставить:
   - `CHAT_BACKEND=responses`
   - primary model проекта
   - fallback model проекта
2. Прогнать ручной smoke:
   - обычный вопрос,
   - knowledge-вопрос,
   - booking-вопрос,
   - forced error / quota path.
3. Проверить логи:
   - `[openai-chat-config]`
   - `path=responses_only`
   - отсутствие деградации JSON-контракта `/chat/api`
4. Перед production сохранить rollback:
   - `CHAT_BACKEND=completions`
5. В production сначала делать soft rollout с готовностью быстро вернуть `completions`.

Заполнить на стенде; **verdict** по чату — только после строки «обычный вопрос» = полезный ответ.

---

## После деплоя

1. `flask db upgrade` (таблица `chat_message`).
2. Проверить `OPENAI_API_KEY`, при необходимости `ASSISTANT_ID` и **`CHAT_BACKEND`**.
3. Production: **`RATELIMIT_STORAGE_URI`** не `memory://`.
4. Один ручной диалог в чате + SQL/лог на две строки в `chat_message`.
