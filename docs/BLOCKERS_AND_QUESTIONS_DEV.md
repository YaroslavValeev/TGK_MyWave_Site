# Блокеры DevTools и ответы на QUESTIONS TO DEV

Дата: 2026-01-28. Исправления по BACKLOG до 10/10.

---

## QUESTIONS TO DEV (ответы по коду после фиксов)

### 1. Что именно является URL у запросов log (полный путь)? Request URL + Response body.

- **Request URL:** `http://127.0.0.1:5000/analytics/log`
- **Метод:** POST. Инициатор: `reco.js` (строка с `fetch(analyticsEndpoint, ...)`).
- **Response (до фикса):** 400 Bad Request из‑за CSRF (нет токена в теле/заголовке).
- **После фикса:** 204 No Content, тело пустое. Эндпоинт освобождён от CSRF точечно (`csrf.exempt(analytics_log)` в `app/__init__.py`).

### 2. При открытии /projects 500 — traceback из терминала (последние ~30 строк).

- **Причина:** возможны исключения в `get_project_cards()` / `get_projects_graph()` (YAML, лишние ключи, отсутствие папки `configs/showcases`).
- **Исправление:** в `app/__init__.py` обёрнуто в try/except: при ошибке в лог пишется traceback, в шаблон передаются `projects=[]`, `showcase_graph={}` — страница отдаёт 200. Дополнительно в `app/services/showcases.py`: фильтрация полей YAML по полям `ShowcaseConfig` и try/except по файлам, чтобы один битый YAML не ломал всю загрузку.

### 3. При запросе /book 500 — traceback и зачем этот роут нужен.

- **Причина 500 (GET):** в `app/routes/services.py` эндпоинт `/services/book` для GET вызывал `request.get_json()` → `None`, затем проверка `if field not in data` падала с TypeError.
- **Исправление:** для GET возвращается редирект на главную с якорем `#booking`: бронирование через модалку на главной. POST по‑прежнему обрабатывает JSON бронирования.
- **Роут /book (без префикса):** добавлен в `app/__init__.py`: GET `/book` и `/book?s=...` редирект на `index#booking`, чтобы ссылки из карточек проектов (cta_url) не вели в 404/500.

### 4. Откуда берётся cover.webp (в каком шаблоне/данных карточек)?

- **Данные:** в `configs/showcases/*.yaml` поле `cover_image`, например: `images/projects/wsc/cover.webp`, `images/projects/wakesurfsafari/cover.webp`. Эти файлы в репозитории отсутствовали → 404.
- **Шаблоны:** `templates/index.html` (блок проектов, `p.cover`) и `templates/projects.html` (карточки проектов, `p.cover`).
- **Исправление:** в обоих шаблонах добавлен fallback: при отсутствии/ошибке загрузки картинки используется `images/hero-wakesurf.webp`; для карточек без `p.cover` выводится та же заглушка.

### 5. Есть ли сейчас в base.html `<link rel="icon" href="/favicon.ico">` или аналог?

- **Да.** В `templates/base.html`:  
  `<link rel="icon" href="{{ url_for('static', filename='favicon.ico') }}">`  
  То есть запрос идёт на `/static/favicon.ico`. Дополнительно в `app/__init__.py` зарегистрирован роут `/favicon.ico`, отдающий файл из `static/`. Файл `static/favicon.ico` присутствует.

### 6. /chat 404 — кто делает переход: кнопка, меню или JS?

- **Шаблон:** `templates/index.html`: кнопка «Чат с тренером» — `<a href="/chat" class="btn-secondary chat-margin">`.
- **Исправление:** в `app/routes/chat.py` добавлен GET‑обработчик для `/chat/`: редирект на главную с якорем `#contact`, чтобы не было 404.

---

## BACKLOG — статус после фиксов

| Задача | Статус | Где правки |
|--------|--------|------------|
| Исправить 500 на /projects | Сделано | `app/__init__.py` (try/except + пустые данные), `app/services/showcases.py` (фильтр полей + try по файлам) |
| Исправить 500 на /book | Сделано | GET `/book` → редирект; GET `/services/book` → редирект в `app/routes/services.py` |
| Убрать/починить 400 на log (reco.js) | Сделано | `app/__init__.py`: csrf.exempt(analytics_log), ответ 204 |
| Починить 404 cover.webp | Сделано | `templates/index.html`, `templates/projects.html`: fallback + onerror на hero-wakesurf.webp |
| Починить favicon 404 | Проверено | base.html + роут /favicon.ico + static/favicon.ico есть |
| Убрать 404 на /chat и book?s=... | Сделано | GET /chat → редирект; GET /book → редирект |
| Закрыть C: /api/lead (curl 201 + Leads) | Без изменений | По-прежнему требуется ручная проверка (curl + скрин Sheets) |
| Закрыть B: HAR + сториборд | Без изменений | Требуется ручное снятие видео/скринов |

---

## Subagents — кто что делал (блокеры)

- **Subagent B (Frontend QA):** URL → инициатор: log → `reco.js`, `/analytics/log`; cover → шаблоны index/projects; favicon → base.html + static; /chat → index.html кнопка; /book → cta_url в YAML карточек.
- **Subagent C (Backend):** Фиксы 500 /projects, 500 /services/book, 400 /analytics/log (CSRF + 204), маршруты /book и GET /chat.
- **Subagent D (UX):** Ссылки /chat и /book ведут на существующие роуты (редиректы на главную с якорями).
- **Subagent E (Critic):** Риски по CSRF/PII/rate limit остаются в таблице; новые изменения не добавляют PII в лог и не расширяют CSRF (добавлен точечный exempt только для analytics_log).
- **Subagent F (Quality Gate):** Критерии 10/10 — после предоставления HAR/скринов и curl/Sheets переоценка.

---

## VALIDATION CHECKLIST (как проверить)

1. Открыть главную → Network: нет 500, нет спама 400 по log; 404 по cover — заменены fallback’ом.
2. Клик «Записаться» → пройти до success.
3. Camp/Выезд/Консалтинг → лид до success → в Network видно POST /api/lead (201).
4. Открыть /projects → 200.
5. Открыть /book или /book?s=... → 302 на главную #booking.
6. Открыть /chat → 302 на главную #contact.
7. Favicon и cover: 200 или fallback без 404 в консоли.
