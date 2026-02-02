# Ответы на QUESTIONS TO DEV (по коду и фактам)

Дата: 2026-01-28. Источник: репозиторий (код), не окружение.

---

## 1. Почему PR не создан? Нет прав на push/PR или просто не сделано?

**По факту:** В Cursor/агент правки вносятся только в **рабочую копию** репозитория. Создание ветки, коммит, `git push` и открытие PR выполняются **вручную** тем, у кого есть доступ к `origin` (разработчик или Ярослав). Агент не имеет доступа к удалённому репо и не может пушить. То есть PR «просто не сделан» со стороны человека с правами — не из‑за отсутствия прав у агента.

**Что сделать:** Выполнить Шаг 1 (команды из NEXT ACTIONS) в корне проекта и открыть PR; после этого прислать PR-ссылку и хеш HEAD.

---

## 2. Вывод `git status --porcelain` и `git diff --name-only`

Выполнить **в корне проекта** (в терминале разработчика):

```bash
git status --porcelain
git diff --name-only
```

Ожидаемые изменённые/новые файлы (по внесённым правкам):

- `templates/base.html`
- `templates/index.html`
- `templates/partials/booking_modals.html`
- `templates/partials/lead_modals.html`
- `templates/shop.html`
- `templates/training_program.html`
- `static/js/booking.js`
- `static/js/lead-forms.js`
- `static/css/style.css`
- `app/__init__.py`
- `app/routes/shop.py`
- `app/routes/api.py`
- `server.js`
- `package.json`
- `package-lock.json`
- `.gitignore`
- `docs/*.md` (несколько файлов)

Точный список даёт только вывод указанных команд в вашем репо.

---

## 3. Выбор по Wake Camp: booking (календарь) или lead (заявка «по запросу»)?

**Зафиксировано по коду: Wake Camp = lead (заявка по запросу).**

- В `templates/index.html`: кнопка Wake Camp имеет `data-lead="camp"`, текст «Запросить программу», **без** `data-modal="booking"`.
- Реализованы: модалка Camp в `partials/lead_modals.html`, обработка в `lead-forms.js`, приём `type=camp` в POST `/api/lead` в `app/routes/api.py`, запись в лист `Leads` при наличии `SPREADSHEET_ID`.

То есть выбран **вариант 1 (рекомендуемый): Camp = lead**, без календарной записи.

---

## 4. Результат проверки `/api/lead`: статус ответа (201/400/403)? Запись в Google Sheets (лист `Leads`)?

**По коду:**

- **CSRF:** В `app/__init__.py` (стр. ~423) зарегистрировано `csrf.exempt(api_bp)`, поэтому POST `/api/lead` **не проверяется на CSRF**. Ожидаемый ответ при успешной отправке: **201** и `{"ok": true, "message": "Заявка принята"}`. Ответ **403** из‑за CSRF от этого эндпоинта не ожидается.
- **Запись в Sheets:** В `app/routes/api.py` при заданном `SPREADSHEET_ID` вызывается `append_record(spreadsheet_id, 'Leads', row)`. Запись в лист `Leads` выполняется при наличии листа `Leads` в указанной таблице; при ошибке записи ответ по-прежнему 201, ошибка логируется.

**Что нужно от тебя:** На стенде/локально отправить лид из модалки и прислать: фактический статус ответа (201/400/403) и скрин строки в листе `Leads` (если запись есть).

---

## 5. Путь подключения модалок: где подключены `booking_modals.html` и `lead_modals.html` (base или index)?

**По коду:**

- **`partials/booking_modals.html`** подключается в:
  - **`templates/index.html`** (стр. ~226) — `{% include 'partials/booking_modals.html' %}`
  - **`templates/services.html`** (стр. ~59)
  - **`templates/services/wake_camp.html`**, `wake_discovery.html`, `wake_challenge.html`, `wakesurf_safari.html` (стр. ~18 в каждом)

- **`partials/lead_modals.html`** подключается только в:
  - **`templates/index.html`** (стр. ~227) — `{% include 'partials/lead_modals.html' %}`

То есть на **главной** (`index.html`) подключены **обе** модалки (booking и lead). В **base.html** они не подключаются.

---

## 6. Node на проде/стенде: `node -v` и чем запускается (pm2/systemd/docker)?

Из репозитория это не следует. Нужны данные от разработчика/инфраструктуры: вывод `node -v` на сервере и способ запуска Node (pm2/systemd/docker).

---

## VALIDATION CHECKLIST — уточнение по Camp

В чеклисте пункт по booking скорректирован с учётом того, что **Camp = lead**:

- **Booking:** hero + **Зал, Катер, Wake Discovery** → модалка бронирования → дата → слот → контакт → success. (**Camp в этот флоу не входит.**)
- **Лиды:** «Тренер на выезде», «Консалтинг», **«Запросить программу» (Wake Camp)** → соответствующие лид-модалки → submit → success.

Остальные пункты чеклиста (меню, секции, товары, `/training-program`, новости, Console, Network) без изменений.
