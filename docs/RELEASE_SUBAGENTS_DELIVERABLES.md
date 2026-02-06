# Артефакты Subagents — пакет кода и доказательств до релиза

Дата: 2026-01-28 (без PR по запросу). Обновлено: 2026-02-03.

---

## Текущий статус (2026-02-03)

**Связанные документы:**
- **`docs/RELEASE_EVIDENCE_AND_QA.md`** — QUESTIONS TO DEV, пакет доказательств (HAR + сториборд 8–12 скринов), фиксы модалок лидов и 404 cover, Quality Gate 8/10 → 10/10 после артефактов.
- **`docs/BLOCKERS_AND_QUESTIONS_DEV.md`** — ответы по блокерам 500/404/400, где править.

**По коду уже сделано:** /projects и /book (200/302), /analytics/log (204 + CSRF exempt), fallback для обложек проектов и витрины товаров, канон WakeSurfPolia, лид-модалки не закрываются от booking.js (ограничение только модалками бронирования + stopPropagation в lead-forms), закрытие лид-модалок по Escape.

**Остаётся вручную (Subagent A/B):** HAR + 8–12 скринов сториборда (см. RELEASE_EVIDENCE_AND_QA.md), при необходимости — видео; curl /api/lead + скрин Leads (C).

---

## [Subagent A — Git/Release Manager]

**Role:** Собрать пакет кода: patch, список файлов, статус.

**Skills:** git workflow, diff/patch.

**Deliverables:**

- **UX_FIXES.patch** — в корне проекта. Если в рабочей копии нет незакоммиченных изменений, файл будет пустым. Тогда выполни локально:
  ```bash
  git diff HEAD > UX_FIXES.patch
  ```
  (или `git diff > UX_FIXES.patch` для unstaged изменений).

- **Вывод команд (текущее состояние репозитория):**
  ```text
  git status --porcelain:
  M  .gitignore
  M  app/routes/ai_concierge_api.py
  M  app/routes/ai_gateway_api.py
  M  app/routes/concierge.py
  M  app/routes/health.py
  M  logs/app.log
  M  requirements.txt
  M  tests/unit/test_ai_concierge_endpoint.py
  M  tests/unit/test_ai_gateway.py
  M  tests/unit/test_core_gateway_real.py
  M  tests/unit/test_tools_retry.py
  M  tests/unit/test_tools_validation.py
  ```

  ```text
  git diff --name-only (vs index): пусто, если всё закоммичено.
  git diff HEAD --name-only: пусто, если нет отличий от HEAD.
  ```

- **Новые файлы (zip):** Собрать вручную все файлы со статусом `??` из `git status --porcelain` (если есть). В текущем срезе новых неотслеживаемых файлов в списке выше нет.

**DoD:** Есть `UX_FIXES.patch` (или он создан по команде выше), сохранён вывод `git status --porcelain` и `git diff --name-only`, при наличии — zip новых файлов.

**Пакет доказательств релиза (альтернатива/дополнение к видео):** HAR + сториборд 8–12 скринов по сценарию из **`docs/RELEASE_EVIDENCE_AND_QA.md`** (01 Hero → 12 Network /projects и /book). Сохранить: 1 HAR-файл + нумерованные скрины.

**Files touched:** корень репозитория, `UX_FIXES.patch`, (опционально) архив новых файлов, папка со скринами + HAR.

**Next:** По команде Ярослава — подготовить PR, ветка `fix/ux-booking-leads-store-preview`.

---

## [Subagent B — Frontend QA (Browser/DevTools)]

**Role:** Пакет доказательств: видео smoke-теста + Console/Network.

**Skills:** DevTools Console/Network, JS, responsive.

**Deliverables (требуют ручного выполнения):**

1. **Видео 60–120 сек** (с видимой адресной строкой):
   - Главная сверху вниз.
   - Booking: зал / катер / Discovery → success.
   - Leads: выезд / консалтинг / camp → success.
   - Товары: 6 карточек → открыть 1 товар.
   - Переход на `/training-program`.

2. **Console:** скрин без красных ошибок после прохода сценария.

3. **Network:** скрин или экспорт HAR (запросы к `/api/lead`, `/api/booking` или иным используемым API без 404/500).

**DoD:** Видео + Console скрин + Network скрин/экспорт приложены к ревью.

**Instructions:** Запустить приложение (`flask run` или через wsgi), открыть главную в браузере, включить запись экрана и DevTools (Console + Network), выполнить сценарий выше, сохранить артефакты.

**Next:** При ревью — точечные правки по скринам при необходимости.

---

## [Subagent C — Backend/API + Security]

**Role:** Проверить `/api/lead` (201), запись в Sheets, CSRF scope.

**Skills:** Flask, CSRF/CORS, curl, Google Sheets.

**Done:**

- Эндпоинт `POST /api/lead` в `app/routes/api.py` (стр. 486–543): принимает JSON с полями `type` (coach_trip | consulting | camp), `contact` и др.; возвращает `201` и `{"ok": true, "message": "Заявка принята"}`; при наличии `SPREADSHEET_ID` пишет строку в лист `Leads`.
- Тип `camp` поддерживается (строки 520–528).

**Evidence (curl — выполнить локально при запущенном сервере):**

```bash
curl -i -X POST http://127.0.0.1:5000/api/lead \
  -H "Content-Type: application/json" \
  -d '{"type":"camp","name":"Test","contact":"+70000000000","message":"test"}'
```

Ожидаемый ответ: `HTTP/1.1 201`, тело `{"ok": true, "message": "Заявка принята"}`. Запись в Google Sheets — только при настроенном `SPREADSHEET_ID` и корректных учётных данных; иначе в логах предупреждение, ответ 201 всё равно возвращается.

**CSRF:**

- В `app/__init__.py` (стр. 504–536) от CSRF освобождены целые blueprint’ы: `api_bp`, `booking_api_bp`, `ai_gateway_bp`, `ai_concierge_bp`, `safari_bp`.
- `/api/lead` входит в `api_bp`, поэтому сейчас exempt весь `api_bp`.

**Рекомендация (DoD):** Сузить exempt до маршрутов, которые реально вызываются без браузерного CSRF-токена (внешние клиенты, тесты). Вариант: не exempt весь `api_bp`, а только конкретные маршруты, например:

```python
from flask_wtf.csrf import csrf_exempt
# после регистрации blueprint:
csrf_exempt(api_lead)   # только view function для /api/lead
```

Остальные маршруты в `api_bp` (например, `/api/chat`, `/api/upload`, `/api/auth/register`) тогда будут защищены CSRF, если это допустимо по сценарию.

**Issues/Risks:** Exempt целого `api_bp` упрощает вызовы из JS/curl, но ослабляет защиту для всех эндпоинтов в нём. Желательно перейти на точечный exempt только для `/api/lead` (и при необходимости для других лид/booking API).

**Files touched:** `app/__init__.py`, `app/routes/api.py`.

**Next:** После ревью — применить точечный CSRF exempt по списку маршрутов.

---

## [Subagent D — UX/Product Consistency]

**Role:** Связность сценариев: Wake Camp = lead, отсутствие падений JS, тексты CTA.

**Done (по коду):**

1. **Wake Camp = lead (вариант 1):**
   - **OK.** На главной в блоке услуг карточка «Wake Camp» с кнопкой «Запросить программу» и `data-lead="camp"` (`templates/index.html`, стр. 64–67).
   - В `lead_modals.html` есть модалка `#lead-modal-camp` с формой `#lead-form-camp`, скрытое поле `type=camp`.
   - В `lead-forms.js` есть `modalIds['camp'] = 'lead-modal-camp'` и обработка отправки с `type: 'camp'`.
   - Бэкенд `/api/lead` принимает `type: "camp"` и пишет в лист Leads.

2. **Страницы без модалок — booking.js / lead-forms.js не падают:**
   - **OK.** В `base.html` подключены `booking.js` и `lead-forms.js` с `defer`. Оба скрипта вешают обработчики на `querySelectorAll('[data-modal="booking"]')` и `querySelectorAll('[data-lead]')`. Если элементов нет, списки пустые, циклы не выполняются — ошибок нет.

3. **Тексты CTA и сценарий:**
   - Wake Camp: «Запросить программу» → lead modal «Запросить программу Wake Camp» — **OK.**
   - Тренер на выезде: «Запросить выезд» → lead modal «Запросить выезд тренера» — **OK.**
   - Консалтинг: «Обсудить запуск» → lead modal — **OK.**

**Deliverables (чеклист):**

| Проверка | Статус |
|----------|--------|
| Wake Camp → кнопка «Запросить программу» → lead modal → success | OK (по коду) |
| На страницах без модалок JS не падает | OK (по коду) |
| Тексты CTA соответствуют сценарию | OK (по коду) |

**Правки текста/CTA:** По текущему коду правок не требуется. При ручной проверке (Subagent B) можно зафиксировать расхождения по формулировкам и вернуть список правок.

**Next:** После видео/скринов от Subagent B — при необходимости точечные правки формулировок или атрибутов.

---

## Сводка для ревью

- **Subagent A:** Выполнить в репозитории `git status --porcelain`, `git diff --name-only`, при необходимости `git diff HEAD > UX_FIXES.patch`, собрать zip новых файлов по `??`.
- **Subagent B:** Снять видео + Console + Network по инструкции выше и приложить к ревью.
- **Subagent C:** Выполнить curl к `/api/lead`, проверить 201 и при наличии Sheets — строку в Leads; принять решение по сужению CSRF exempt.
- **Subagent D:** Чеклист и связность по коду выполнены; финальные правки текста/CTA — по результатам ревью и видео.

После предоставления **patch + новые файлы + видео/DevTools + curl/Sheets** — ревью «по строкам» и финальный релизный чеклист.

---

## [Subagent E — Critic (Devil's Advocate)]

**Role:** Риски, регрессии, «ломаем сценарии».

**Skills:** risk assessment, threat modeling, regression hunting.

**Deliverables:** минимум 10 конкретных уязвимостей/рисков + как воспроизвести + как исправить.

| # | Риск | Воспроизведение | Исправление |
|---|------|-----------------|-------------|
| 1 | **CSRF exempt слишком широко** — exempt целого `api_bp` в `app/__init__.py` (506) снимает защиту со всех маршрутов (`/api/chat`, `/api/upload`, `/api/auth/register`, `/api/lead` и др.). | Любой POST к этим эндпоинтам без токена из другого сайта. | Exempt только view для `/api/lead` (и при необходимости для booking API); остальные оставить под CSRF. |
| 2 | **JS падает при отсутствии DOM** — `booking.js` при инициализации обращается к `document.getElementById("modalCalendar")` и др. (стр. 24–43). На странице без модалок эти элементы `null`; при последующем обращении (например, по клику на другой элемент или по таймеру) возможен TypeError. | Открыть страницу без включения partials с модалками (например, статичную или другую ветку шаблона), выполнить действие, триггерящее логику booking. | Перед использованием проверять `if (UI.calendarModal) { ... }` или выходить из `initializeBooking()` раньше, если ключевых элементов нет. |
| 3 | **Логирование сырых лид-данных** — в `api_lead()` (api.py:505) `current_app.logger.info("Lead received: type=%s, data=%s", lead_type, data)` пишет в лог весь `data` (контакты, сообщения). При централизованных логах — риск утечки PII. | Отправить лид с контактом/сообщением, проверить `logs/app.log`. | Логировать только `type` и хеш или не логировать тело; не писать contact/message в plaintext. |
| 4 | **Логи в репозитории** — `logs/app.log` попал в `git status` (modified). В `.gitignore` есть `logs/`, но файл уже был закоммичен ранее. | `git status` — видно `M logs/app.log`. | Удалить из индекса: `git rm --cached logs/app.log`; убедиться, что `logs/` в `.gitignore`; не коммитить логи. |
| 5 | **Нет rate limit на /api/lead** — эндпоинт принимает POST без ограничения частоты; возможен спам лидов и DoS. | Многократно отправить `curl -X POST .../api/lead` с разными данными. | Подключить Flask-Limiter или middleware по IP/ключу для POST `/api/lead`. |
| 6 | **Пустые/невалидные данные в Sheets** — при отсутствии полей `data.get("location", "")` и т.д. в лист пишутся пустые строки; структура листа «Leads» может ожидать колонки в определённом порядке. | Отправить лид с минимальным телом `{"type":"camp","contact":"+7"}`, проверить строку в таблице. | Валидировать обязательные поля по типу лида; при несовпадении структуры — возвращать 400 или логировать ошибку. |
| 7 | **Дубли id модалок** — если на одной странице дважды подключить `lead_modals.html` или смешать старую/новую версию, возможны два элемента с `id="lead-modal-camp"`. | Вставить partial дважды в шаблон, открыть lead modal. | Использовать один include модалок; проверять в ревью шаблонов отсутствие дублей id. |
| 8 | **XSS при отображении ответа/ошибки** — в `lead-forms.js` (стр. 79) `successEl.textContent = '...'` безопасно; но в других местах (chat.js, calculator) есть `innerHTML` с данными — при расширении лид-ответов на HTML риск XSS. | Если когда-либо выводить ответ API в innerHTML без санитизации. | Всегда использовать `textContent` или санитизировать вывод; не вставлять пользовательский ввод в innerHTML. |
| 9 | **Зависимость от SPREADSHEET_ID** — при отсутствии или неверном `SPREADSHEET_ID` запись в Sheets падает с warning, но ответ 201. Пользователь считает, что заявка «принята», а в таблице её нет. | Выключить/не задать SPREADSHEET_ID, отправить лид, проверить ответ и таблицу. | В режиме без Sheets возвращать 503 или явное предупреждение в ответе; или документировать «только логирование» для dev. |
| 10 | **404 на static** — при переименовании/удалении файла (например, `lead-forms.js`, `booking.js`) или опечатке в `url_for('static', ...)` страница загрузится, но скрипт не выполнится; сценарий «сломается» без явной ошибки в консоли, если не смотреть вкладку Network. | Указать неверный путь к JS в base.html, перезагрузить страницу, открыть Network. | Проверять при релизе загрузку всех критичных JS (Network); при необходимости — тест или скрипт проверки 200 для перечисленных static. |
| 11 | **Регрессия навигации** — если в base.html изменить якоря или убрать ссылки «Товары»/«Проекты», секции станут недоступны из меню. | Удалить ссылку `/#store` или `/#projects`, проверить клик в шапке. | Smoke-чек: главная → клик по каждому пункту меню → ожидаемая секция/страница. |
| 12 | **CORS для /api/lead** — если позже подключать вызовы с другого домена, текущая настройка CORS (в extensions и т.д.) может блокировать запросы. | Вызвать fetch('/api/lead') с другого origin. | При необходимости добавить/проверить CORS для API лидов только с доверенных origins. |

**DoD:** Критические риски либо устранены, либо оформлены как блокеры в тикетах/чеклисте.

---

## [Subagent F — Quality Analyst / Scorekeeper (0–10)]

**Role:** Итоговая оценка по рубрике и возврат на доработку до 10/10.

**Skills:** QA rubric, acceptance criteria, release gatekeeping.

**Rubric (кратко):**

- Есть UX_FIXES.patch + новые файлы (воспроизводимо).
- Видео + Console + Network приложены.
- booking + leads + товары + training-program проходят smoke без ошибок.
- /api/lead даёт 201 и пишет в Leads.
- Критик не нашёл блокирующих рисков (или они закрыты).
- Нет явных регрессий по навигации/видимости.

**Score: 5/10**

**Why (3–7 пунктов):**

1. **Patch/новые файлы** — UX_FIXES.patch в текущем срезе пуст (всё закоммичено или окружение без локальных изменений); zip новых файлов не собран. Воспроизводимость «пакета кода» не доказана.
2. **Видео + DevTools** — видео 1–2 мин, Console и Network скрины не приложены; smoke по сценариям не зафиксирован.
3. **/api/lead** — curl не выполнен при запущенном сервере; скрин строки в Leads и подтверждение записи отсутствуют.
4. **CSRF** — рекомендация по сужению exempt дана, но не применена; остаётся риск (см. Subagent E).
5. **Критик** — выявлены риски (логирование PII, rate limit, логи в git); блокеры не закрыты.
6. **Плюсы:** UX-связность (Camp = lead, CTA, JS без модалок) по коду проверена; эндпоинт и контракт /api/lead реализованы; документ с артефактами и инструкциями подготовлен.

**Required fixes to reach 10/10 (по файлам/местам):**

| Кто | Что | Где / как |
|-----|-----|-----------|
| A | Воспроизводимый пакет кода | В корне: `git diff HEAD > UX_FIXES.patch`; zip файлов со статусом `??` из `git status --porcelain`. |
| B | Видео + Console + Network | 1–2 мин с адресной строкой: главная → booking → leads → товары → /training-program; скрины без красных ошибок и 404/500. |
| C | Подтверждение /api/lead и CSRF | Выполнить curl, приложить ответ 201 и скрин строки в листе Leads; сузить CSRF exempt до маршрута `/api/lead` (и при необходимости booking) в `app/__init__.py`. |
| C | Логирование лидов | В `app/routes/api.py` в `api_lead()` не логировать полное `data` (убрать PII из лога). |
| A | Логи не в репозитории | `git rm --cached logs/app.log` (если ещё в индексе), не коммитить logs. |
| E/C | Rate limit для /api/lead | По желанию: ограничение по IP/ключу для POST /api/lead. |

**Re-check requirements (что принести повторно):**

- **Subagent A:** UX_FIXES.patch (непустой при наличии изменений) + zip новых файлов + вывод `git status --porcelain` и `git diff --name-only`.
- **Subagent B:** Видео 1–2 мин + Console скрин + Network скрин/экспорт.
- **Subagent C:** Вывод `curl -i .../api/lead` (201 + тело), скрин строки в листе Leads, краткий вывод по CSRF (что exempt и почему).
- **Subagent F:** Повторная оценка после предоставления артефактов и исправлений из таблицы выше; цель — 10/10 или явный список блокеров.
