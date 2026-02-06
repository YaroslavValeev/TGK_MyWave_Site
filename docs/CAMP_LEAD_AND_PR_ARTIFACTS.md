# Camp = лид (вариант А) + ответы на QUESTIONS TO DEV + артефакты для PR

Дата: 2026-01-28.

---

## 1. Решение по Camp (зафиксировано)

**Выбрали вариант А: Camp = заявка (по запросу).**

- У кнопки Wake Camp убран `data-modal="booking"`.
- Добавлен `data-lead="camp"`, текст кнопки: «Запросить программу».
- Реализована отдельная лид-модалка Camp: желаемые даты/окно, уровень, цель, бюджетный коридор (опц.), контакт. Отправка в POST `/api/lead` с `type=camp`, запись в лист `Leads` (при наличии SPREADSHEET_ID).

**Файлы:** `templates/index.html`, `templates/partials/lead_modals.html`, `static/js/lead-forms.js`, `app/routes/api.py`.

---

## 2. Ответы на QUESTIONS TO DEV

**1. Почему Шаг 1 (ветка/коммит/PR) не сделан тобой? Кто пушит?**  
Шаг 1 делается в репозитории разработчиком: создание ветки, коммит, пуш и открытие PR выполняет тот, у кого есть права на origin (ты или Ярослав). В Cursor/агент правки только в рабочей копии; пуш и PR — вне доступа агента.

**2. Ссылка на репозиторий / origin и права на push/PR**  
Из кода репо не виден удалённый URL. Нужно от тебя: `git remote -v` и подтверждение, что у тебя есть права на push и создание PR.

**3. Точный список изменённых файлов и diff**  
Выполни в корне проекта и пришли вывод:

```bash
git status --porcelain
git diff --stat
```

Ожидаемые файлы (по внесённым правкам):  
`templates/base.html`, `templates/index.html`, `templates/partials/booking_modals.html`, `templates/partials/lead_modals.html`, `templates/shop.html`, `templates/training_program.html`, `static/js/booking.js`, `static/js/lead-forms.js`, `static/css/style.css`, `app/__init__.py`, `app/routes/shop.py`, `app/routes/api.py`, `server.js`, `package.json`, `package-lock.json`, `.gitignore`, `docs/*.md` и др.

**4. Camp — заявка/лид или календарная запись?**  
Зафиксировано: **Camp = заявка/лид (по запросу)**, вариант А. Реализовано в коде (см. п. 1).

**5. Скрины success бронирования и success лид-формы**  
Должны быть от тебя после проверки на стенде: скрин после успешной записи (booking) и скрин после отправки лид-формы (выезд/консалтинг/Camp).

**6. /api/lead и CSRF**  
В `app/__init__.py` зарегистрировано `csrf.exempt(api_bp)`, то есть все роуты blueprint `api_bp`, включая POST `/api/lead`, **не проверяются CSRF**. Ответ при успешной отправке: **201** и `{"ok": true, "message": "Заявка принята"}`. Блокировки по CSRF (403) от этого эндпоинта не будет. Запись в лист `Leads` выполняется при заданном `SPREADSHEET_ID` и наличии листа `Leads`; при ошибке записи в Sheets ответ по-прежнему 201, ошибка логируется.

---

## 3. NEXT ACTIONS (напоминание)

### Шаг 1 — PR

В корне проекта:

```bash
git checkout -b fix/ux-booking-leads-store-preview
git status --porcelain
git add -A
git commit -m "UX: anchors, booking modals, leads (coach/consulting/camp), products preview, training program"
git push -u origin fix/ux-booking-leads-store-preview
```

Далее: открыть PR, в описание вставить резюме изменений, список страниц для проверки (`/`, `/shop`, `/projects`, `/blog`, `/training-program`) и чеклист проверки.

**Вернуть:** ссылку на PR, хеш HEAD, список файлов в PR.

### Шаг 2 — Camp

Уже сделано: **вариант А** (Camp = лид). Остаётся прислать видео клика по Camp и результат (успешная отправка заявки).

### Шаг 3 — Пакет доказательств

Видео 1–2 мин, Console+Network, при использовании Node — `node -v`, способ запуска, логи (как в твоём запросе).

### Шаг 4 — Smoke на staging

После мержа/деплоя — те же проверки на staging URL.

---

## 4. VALIDATION CHECKLIST (без изменений)

- Меню Главная/Товары/Проекты → якоря, скролл.
- Главная: секции Услуги, Товары, Проекты, Новости.
- Booking: «Записаться» → модалка → дата → слот → контакт → success.
- Leads: «Запросить выезд», «Обсудить запуск», **«Запросить программу» (Camp)** → лид-формы → success.
- Товары: 6 карточек на главной, `/shop`, нейминг.
- `/training-program`: уровни и CTA.
- Console без ошибок, Network без 404/500 по критичным запросам.
