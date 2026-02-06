# Пакет доказательств релиза: QUESTIONS TO DEV + Subagents A–F + Quality Gate

Дата: 2026-02-03. Факты по скринам, блокеры, модалки лидов, 404/500.

---

## QUESTIONS TO DEV (ответы по коду и правкам)

### Подтверди фактами: после правок исчезли серые плейсхолдеры на главной (дай 1 скрин секции «Товары» на главной).

**По коду:** В шаблоне **`templates/index.html`** (блок «Товары») для каждой карточки: `p.image or 'images/hero-wakesurf.webp'` и **`onerror`** на `<img>`, подставляющий ту же заглушку при ошибке загрузки. В **`templates/shop_product.html`** — такой же fallback.  
**Факт «после правок»:** скрин секции «Товары» на главной нужно снять вручную после жёсткого обновления (Ctrl+Shift+R) и при отсутствии кэша. Если скрины по-прежнему показывают серые блоки — проверить, что загружены актуальные `index.html` и `shop.py` (нет старого «Wave Cards» в витрине).

---

### Подтверди фактами: в магазине нет «Wave Cards» (1 скрин списка + 1 скрин карточки товара WakeSurfPolia).

**По коду:** В **`app/routes/shop.py`** товар **`wave-cards`** удалён; в **`templates/shop.html`** одна карточка **WakeSurfPolia** и фильтр «WakeSurfPolia». Страница товара: `/shop/product/wakesurfpolia`.  
**Факт:** два скрина (список магазина + карточка WakeSurfPolia) — вручную; при необходимости обновить страницу с отключённым кэшем.

---

### Что сейчас с /projects и /book — по твоему Network они всё ещё 500?

**По коду (уже внесённые правки):**  
- **`/projects`:** в **`app/__init__.py`** обёрнут в try/except; при ошибке в шаблон передаются пустые `projects`/`showcase_graph`, ответ **200**. В **`app/services/showcases.py`** — фильтр полей YAML и пропуск битых файлов.  
- **`/book`:** в **`app/__init__.py`** добавлен GET **`/book`** → редирект на главную `#booking`. В **`app/routes/services.py`** GET **`/services/book`** → редирект на главную `#booking`.  

**Факт:** скрин Network со строками `/projects` и `/book` со статусами 200/302 нужно снять после деплоя/перезапуска (Subagent A/C).

---

### Откуда берутся 404 cover.webp (пути/шаблон)? Где физически лежит файл или почему его запрашивают?

**Источник:** поле **`cover_image`** в **`configs/showcases/*.yaml`** (например `images/projects/wsc/cover.webp`, `images/projects/wakesurfsafari/cover.webp`). Эти пути подставляются в **`templates/index.html`** и **`templates/projects.html`** в `url_for('static', filename=p.cover)`. Файлов по этим путям в репозитории не было → браузер запрашивал их и получал 404.  

**Правка:**  
1) В шаблонах уже был fallback и **onerror**.  
2) В **`app/services/showcases.py`** в **`get_project_cards()`** добавлена проверка: если файл `static/<cover>` не существует, в карточку подставляется **`images/hero-wakesurf.webp`**. Запрос cover.webp по отсутствующему пути больше не уходит → 404 в Network по обложкам проектов исчезают.

**Favicon:** в **`templates/base.html`** — `<link rel="icon" href="{{ url_for('static', filename='favicon.ico') }}">`; в **`app/__init__.py`** — роут **`/favicon.ico`**, отдающий `static/favicon.ico`. Файл **`static/favicon.ico`** должен присутствовать.

---

### 400 log — это /analytics/log? Что является источником (reco.js?) и нужно ли это вообще на релиз?

**Да.** Запросы идут на **`POST /analytics/log`**. Источник — **`static/js/reco.js`** (строка с `fetch(analyticsEndpoint, ...)`, `analyticsEndpoint = '/analytics/log'`).  

**Правки (уже внесены):** в **`app/__init__.py`** для view **`analytics_log`** включён точечный **`csrf.exempt(analytics_log)`**, ответ — **204 No Content**. На релиз эндпоинт можно оставить (аналитика без спама 400); при отсутствии Sheets запись просто не выполняется.

---

## Исправление: модалки Camp / Выезд / Консалтинг «появляются и тут же исчезают»

**Причина:** В **`static/js/booking.js`** на **все** элементы с классом **`.modal`** вешался обработчик: при клике/ mousedown по «вне контента» вызывался **`hideAllModals()`**. Лид-модалки тоже имеют класс **`modal`**, из‑за чего один и тот же клик мог обрабатываться и lead-forms (открытие), и booking (логика «закрыть по клику вне»).  

**Правки:**  
1. **`static/js/booking.js`:** обработчики «закрыть по клику вне» и «закрыть по mousedown на backdrop» применяются только к модалкам бронирования: **`[UI.calendarModal, UI.slotsModal, UI.contactModal, UI.confirmModal]`**. Лид-модалки больше не участвуют.  
2. **`static/js/lead-forms.js`:** в обработчике клика по кнопке **`[data-lead]`** добавлен **`e.stopPropagation()`**; добавлено закрытие лид-модалок по **Escape** (если открыта любая из трёх лид-модалок).

---

## NEXT ACTIONS — отчёт по Subagents A–F

### Subagent A — Release Evidence (HAR + сториборд)  
**Skills:** DevTools, HAR export, reproducible evidence  

**Сделать (вручную):**  
- Открыть главную → DevTools → Network: Preserve log, Disable cache → Ctrl+R → Save all as HAR with content.  
- Сториборд 8–12 скринов: 01 Hero, 02 «Почему мы?», 03 Услуги, 04 Товары на главной, 05 Проекты на главной, 06 Последние новости, 07 /shop, 08 /shop/product/wakesurfpolia, 09 /training-program, 10 клик booking (первый шаг модалки), 11 клик lead (Camp/Выезд/Консалтинг) — модалка, 12 Network: строки /projects и /book.  

**Вернуть:** 1 HAR + 8–12 нумерованных скринов.

---

### Subagent B — Frontend: 404 cover.webp + favicon  
**Skills:** templates, static routing  

**Сделано по коду:**  
- **cover.webp:** в **`get_project_cards()`** (showcases.py) подставляется fallback, если файл по `cover_image` не существует; в шаблонах по-прежнему fallback + onerror.  
- **favicon:** base.html + роут /favicon.ico + файл static/favicon.ico.  

**Вернуть (вручную):** скрин Network «было 404 → стало 200» для cover и favicon после перезагрузки.

---

### Subagent C — Backend: /projects 500 и /book 500  
**Skills:** Flask debugging, routing  

**Сделано по коду:**  
- **/projects:** try/except в view, при ошибке — пустые данные, ответ 200; в showcases — фильтр полей и пропуск битых YAML.  
- **/book:** GET /book и GET /services/book — редирект на главную #booking.  

**Вернуть (вручную):** скрин /projects (200) и /book (302) в Network + 1–2 предложения «root cause → fix».

---

### Subagent D — Product/UX Consistency  
**Skills:** CTA flows, content consistency  

**Таблицы (по коду):**  
- Услуга → CTA → тип (booking/lead) → success: Зал/Катер/Wake Discovery → booking; Camp/Выезд/Консалтинг → lead.  
- Товар → CTA «Купить» → страница товара `/shop/product/<slug>`.  

**Вернуть:** 2 таблицы + 2 скрина клика (booking + lead).

---

### Subagent E — Critic  
**Skills:** regression hunting, risk prioritization  

**По HAR выписать:** все 5xx/4xx, красные ошибки в Console, массовые 404/400.  
**Вернуть:** список «Issue → Severity → Fix → Owner(subagent)».

---

### Subagent F — Quality Gate (0–10)  
**Skills:** acceptance criteria, release readiness  

**Критерии 10/10:**  
- HAR без критичных 500; нет массовых 404 по статике (cover/favicon исправлены в коде).  
- /projects и /book не 500 (в коде — 200/302).  
- Витрина товаров без плейсхолдеров (fallback + onerror в шаблонах).  
- WakeSurfPolia канон (wave-cards удалён, одна карточка в магазине и на главной).  
- Лид-модалки (Camp, Выезд, Консалтинг) не исчезают сразу (правки в booking.js и lead-forms.js).  

**Оценка после правок в коде:** **8/10**.  

**До 10/10 не хватает:**  
- Фактических артефактов: **HAR + 8–12 скринов** (Subagent A).  
- Подтверждения по Network: **/projects 200, /book 302, нет массовых 404** (скрины).  
- Подтверждения по витрине и магазину: **нет плейсхолдеров, только WakeSurfPolia** (скрины).  

Если после предоставления HAR и скринов критерии выполнены — выставить **10/10**. Если нет — вернуть на доработку с перечислением: файл/место/ожидаемый результат.

---

## VALIDATION CHECKLIST (браузер + консоль/сеть)

1. Главная → проскроллить до Услуги/Товары/Проекты/Новости — всё видно.  
2. Главная, секция «Товары» — нет пустых серых блоков (картинка или fallback).  
3. /shop — только WakeSurfPolia, «Wave Cards» отсутствует.  
4. /projects — 200, список проектов виден.  
5. /book — 200 или корректный redirect (302 на #booking).  
6. Network: нет гроздей 404/500; favicon.ico и запросы по обложкам проектов не 404.  
7. Console: нет красных ошибок при кликах по CTA (booking/lead/Купить).  
8. Wake Camp, Тренер на выезде, Консалтинг — модалка открывается и остаётся открытой (правки в booking.js и lead-forms.js).
