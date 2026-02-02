# Артефакты ревью и протокол «приземления на реальность»

Дата: 2026-01-28. Роль: ревьюер/приёмка. Репозиторий: локальный путь `e:\Проекты MyWave\Site_MyWave` (ветка `main`).

---

## 1. Пакет фактов (Шаг 0 — вывод по репо)

```text
git rev-parse --abbrev-ref HEAD  →  main
git rev-parse HEAD               →  11085b01266e39c1283a2e4fae83038d9ac6028e
git log -1 --oneline             →  11085b01 docs: current main hash 13daf490 in Decision Log P1
```

**Изменённые файлы относительно последнего коммита (не закоммичены):**

- `app/__init__.py` — правки home(): projects_preview, latest_blog_post
- `app/routes/shop.py` — добавлены товары certificate-10, balance-board-newstyle
- `static/css/style.css` — стили проектов/блога
- `templates/base.html` — пункты навигации «Товары», «Проекты»
- `templates/index.html` — секции Проекты/Последние новости, карточки услуг/товаров, ссылки
- `templates/shop.html` — карточки NewStyle, Сертификат, фильтр «Сертификаты»

**Новые/доп. изменения в этом цикле:**

- `server.js` — убран `require('node-fetch')`, используется global fetch (Node 18+)
- `package.json` — удалён `node-fetch`, добавлен `"engines": { "node": ">=18" }`
- `.gitignore` — убраны строка `EOF` и правило `*.json` (следы конфликта/перебор)

**PR/ветка:** единой ветки с «всеми правками» в удалённом репо нет — правки есть только в рабочей копии (main). Для приёмки нужны: `repo_path_or_url`, ветка/тег, ссылка на PR или архив `git diff`.

**Артефакт diff (текущая рабочая копия):** `docs/changes.diff` — diff относительно HEAD для файлов: server.js, package.json, .gitignore, app/__init__.py, templates/base.html, templates/index.html, templates/shop.html, app/routes/shop.py, static/css/style.css.

---

## 2. STATUS SNAPSHOT (по фактам репо)

- **Подтверждено по файлам:** в проекте есть Flask (app/, templates/, static/), Node-слой (`server.js`, `package.json`). Роуты: shop, blog, projects (в app/__init__.py), services, wake_industry, projects_safari, projects/wakesurf_challenge.
- **Подтверждено по коду:** навигация «Товары»/«Проекты» добавлена в `templates/base.html` (стр. ~108–110). Секции «Проекты» и «Последние новости» — в `templates/index.html`. Источники: проекты — `configs/showcases/*.yaml`, товары — `app/routes/shop.py` PRODUCTS, новости — `app/services/blog/store.py` get_latest_post().
- **Критический риск (снят патчем):** `node-fetch@3` (ESM-only) + `require("node-fetch")` в `server.js` → падение чат-сервиса. **Исправлено:** использование нативного `fetch` (Node 18+), зависимость `node-fetch` удалена.
- **Критический риск (снят патчем):** в `.gitignore` были строка `EOF` и правило `*.json` → грязные коммиты/игнор нужных JSON. **Исправлено:** удалены `EOF` и `*.json`.
- **Риск безопасности:** секреты в `.env` — в `.gitignore` уже есть `.env`/`*.env`; для релиза — не коммитить `.env`, ротация ключей при утечке.
- **Видимость секций:** без staging/prod URL и скрина «часть сайта не видна» воспроизвести 1:1 нельзя; по коду секции и роуты присутствуют (см. п. 4).

---

## 3. Где что лежит (файлы + строки)

| Что | Файл | Строки / примечание |
|-----|------|----------------------|
| Навигация (Товары, Проекты) | `templates/base.html` | ~108–110: `<li><a href="{{ url_for('shop.shop_index') }}">Товары</a></li>`, `url_for('projects_page')` |
| Секция Услуги (5 карточек) | `templates/index.html` | ~36–90: service-card × 6 (Тренировка, Катер, Wake Discovery, Wake Camp, Тренер на выезде, Консалтинг) |
| Секция Товары + «Все товары» | `templates/index.html` | ~72–99: cards-grid, ссылки на shop.product, store-more → shop.shop_index |
| Секция Проекты | `templates/index.html` | ~101–130: projects_preview из get_project_cards()[:3], projects-more → projects_page |
| Блок «Последние новости» | `templates/index.html` | ~138–152: latest_blog_post из get_latest_post(), иначе fallback + ссылка в блог |
| Контекст главной (projects_preview, latest_blog_post) | `app/__init__.py` | home(): get_project_cards(), get_latest_post(), render_template(..., projects_preview, latest_blog_post) |
| Каталог товаров | `app/routes/shop.py` | PRODUCTS: balance-board, balance-board-big, poncho, wave-cards, wakesurfpolia, balance-board-pro, balance-board-newstyle, certificate-10 |
| Страница магазина | `templates/shop.html` | Карточки + фильтр «Сертификаты» |
| Проекты (YAML) | `configs/showcases/` | sochi_camp.yaml, wakesurf_safari.yaml |
| Роут /projects | `app/__init__.py` | projects_page() → get_project_cards(), projects.html |
| Чат (Node) | `server.js` | POST /chat, до патча — require('node-fetch'); после — global fetch |

---

## 4. BACKLOG — статусы по фактам репо

| # | Задача | Статус | Комментарий |
|---|--------|--------|-------------|
| 1 | Привязаться к фактам: PR/коммит, URL, шаги воспроизведения | **Open** | Нужны от разработчика: repo_url, ветка/PR, staging/prod URL, шаги «где не видно» |
| 2 | Локализовать root-cause «не вижу часть сайта» | **Open** | Нужны консоль/сеть/логи; по коду секции есть |
| 3 | Проверка видимости: Услуги/Товары/Проекты/Новости | **Done (по коду)** | base.html + index.html + роуты есть; приёмка — по URL/скрину |
| 4 | UX раскрытия карточек (клик → модалка/страница → CTA) | **Partial** | Товары: ссылка на страницу; модалки товаров на главной нет |
| 5 | Модалка «Сертификат на 10 занятий» + общий механизм | **Open** | В репо модалок товаров нет (catalog-modal не найден) |
| 6 | «Тренировочная программа для подготовки» | **Open** | Отдельного контента/страницы нет |
| 7 | Нейминг «Пончо — Комбез» vs «Пончо для сёрфинга» | **Open** | В каталоге: «Пончо для сёрфинга», slug poncho |
| 8 | «Последние новости»: источник, кеш, fallback | **Done (по коду)** | get_latest_post(), fallback в index.html |
| 9 | node-fetch ESM, .gitignore, .env | **Done (патчи)** | server.js → global fetch; .gitignore очищен; .env не в репо |
| 10 | Регрессии: сборка, адаптив, доступность, SEO | **Open** | Нужен прогон Lighthouse/ручные проверки |

---

## 5. Ответы на QUESTIONS TO DEV (из репо)

- **1. repo_path_or_url, ветка, PR, diff**  
  Локально: `e:\Проекты MyWave\Site_MyWave`, ветка `main`, коммит `11085b01`. Правки видимости/навигации/товаров — в рабочей копии, не в последнем коммите. Нужны: удалённый URL, ветка/PR и `git diff` или список файлов из разработчика.

- **2. Staging/prod URL и шаги**  
  Из репо не известны. Нужны от разработчика.

- **3. Скрин/видео главной, /shop, /projects, блог**  
  Нужны от разработчика.

- **4. Консоль DevTools (Console + Network)**  
  Нужны от разработчика в момент проблемы.

- **5. Карточки товаров на главной — модалки или страница?**  
  Сейчас в коде: переход на страницу товара (`url_for('shop.product', slug=...)`). Отдельного JS/модалок товаров на главной нет.

- **6. Источники данных и поля видимости**  
  - Проекты: `configs/showcases/*.yaml`, список через `get_project_cards()` (channel='projects').  
  - Товары: `app/routes/shop.py` PRODUCTS (статический словарь).  
  - Последние новости: `app/services/blog/store.py` get_latest_post() (Sheets/БД). Поля видимости: в блоге — по логике store (published_at и т.д.); в YAML — `status`, `channels`.

- **7. Node-слой на проде**  
  Из репо не известно (pm2/systemd/docker). Нужны логи процесса от разработчика.

---

## 6. Выполненные патчи (критические блокеры)

### 6.1. server.js — убран require('node-fetch')

- **Причина:** node-fetch@3 только ESM, `require("node-fetch")` падает.
- **Правка:** использование global `fetch` (Node 18+), в package.json добавлен `"engines": { "node": ">=18" }`, зависимость `node-fetch` удалена.
- **Файлы:** `server.js`, `package.json`.

### 6.2. .gitignore — следы конфликта и перебор по *.json

- **Причина:** строка `EOF` и правило `*.json` (риск игнорирования package.json и конфигов).
- **Правка:** удалены `EOF` и `*.json`, комментарий про секреты уточнён.
- **Файл:** `.gitignore`.

---

## 7. VALIDATION CHECKLIST (для ручной проверки после деплоя)

- [ ] Главная: секция Услуги видна, 6 карточек (Зал, Катер, Wake Discovery, Wake Camp, Тренер на выезде, Консалтинг).
- [ ] Главная: секция Товары видна, есть «Все товары», карточки ведут на страницы товаров.
- [ ] Главная: секция Проекты видна, есть «Все проекты».
- [ ] Главная: блок «Последние новости» — пост или fallback + ссылка в блог.
- [ ] Консоль без красных ошибок, Network без 404/500 по ключевым ресурсам.
- [ ] /shop открывается, фильтр «Сертификаты», страницы товаров не 404.
- [ ] /projects открывается, страницы проектов не 404.
- [ ] /blog открывается, последний пост кликабелен.
- [ ] Node-сервис чата: процесс жив, endpoint отвечает 200 (Node 18+).

---

## 8. DoD (Definition of Done) для приёмки

- Есть артефакт: PR или `git diff` с правками видимости/навигации/товаров/проектов/новостей.
- Есть staging/prod URL и шаги воспроизведения «часть сайта не видна» (или подтверждение, что видно).
- Консоль/сеть/логи без критических ошибок при открытии главной и ключевых страниц.
- Критические блокеры (node-fetch, .gitignore) закрыты коммитами (уже внесены в рабочую копию).
- Чеклист п. 7 пройден по факту (скрин/видео или описание результата).

После первого ответа разработчика с PR/URL/шагами ревью отрабатывается по протоколу 1→5 с обновлением backlog.
