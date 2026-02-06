# Ответ ревьюера на запрос разработчика (артефакты и факты)

Дата: 2026-01-28. Все ответы — по фактам репозитория в текущей рабочей копии.

---

## 1. Ссылка на PR / запушенная ветка

**Факт:** В репо правки есть только в **рабочей копии** (ветка `main`), они **не закоммичены и не запушены**. Отдельного PR или запушенной ветки с этими коммитами **нет**.

**Что сделать:**  
Создать ветку, закоммитить все перечисленные ниже файлы, запушить и открыть PR. После этого прислать ссылку на PR (или на ветку).

**Список файлов для коммита:**

- `server.js`
- `package.json`
- `package-lock.json` (обновлён: удалён `node-fetch`)
- `.gitignore`
- `app/__init__.py`
- `templates/base.html`
- `templates/index.html`
- `templates/shop.html`
- `app/routes/shop.py`
- `static/css/style.css`

Команды (пример):

```bash
git checkout -b fix/nav-sections-node-fetch-gitignore
git add server.js package.json package-lock.json .gitignore app/__init__.py templates/base.html templates/index.html templates/shop.html app/routes/shop.py static/css/style.css
git commit -m "fix: nav Товары/Проекты, секции главной, node-fetch→native fetch, .gitignore"
git push origin fix/nav-sections-node-fetch-gitignore
# затем открыть PR в веб-интерфейсе
```

---

## 2. Файлы docs/changes.diff и docs/REVIEW_ARTIFACTS_AND_PROTOCOL.md

**Где лежат (построчная сверка):**

- **`docs/changes.diff`** — diff относительно `HEAD` по файлам: `.gitignore`, `app/__init__.py`, `app/routes/shop.py`, `package.json`, `server.js`, `static/css/style.css`, `templates/base.html`, `templates/index.html`, `templates/shop.html`.  
  В diff кириллица может отображаться в UTF-8 как кракозябры (зависит от настроек git). Содержимое и патчи корректны.

- **`docs/REVIEW_ARTIFACTS_AND_PROTOCOL.md`** — полный документ с пакетом фактов, STATUS, BACKLOG, файлы+строки, ответы на вопросы, чеклист и DoD.

**Текст для сверки:**  
Оба файла находятся в репо по путям выше. Ниже — краткое содержание; полный текст см. в самих файлах.

**docs/changes.diff (сводка изменений):**

- **.gitignore:** удалены строка `EOF` и правило `*.json`, добавлен комментарий про секреты.
- **app/__init__.py:** в `home()` добавлены `get_project_cards()[:3]`, `get_latest_post()`, в шаблон передаются `projects_preview`, `latest_blog_post`.
- **app/routes/shop.py:** в PRODUCTS добавлены `balance-board-newstyle`, `certificate-10`.
- **package.json:** добавлен `"engines": { "node": ">=18" }`, удалена зависимость `node-fetch`, исправлена запятая.
- **server.js:** убран `require("node-fetch")`, используется `globalThis.fetch` с проверкой и fallback-ошибкой.
- **static/css/style.css:** добавлены `.projects-section`, `.projects-preview-list`, `.project-preview-card`, `.projects-more`, `.store-more`, `.blog-latest`, `.blog-excerpt`, `.blog-more`.
- **templates/base.html:** в навигацию добавлены пункты «Товары» (`url_for('shop.shop_index')`), «Проекты» (`url_for('projects_page')`).
- **templates/index.html:** две новые карточки услуг (Тренер на выезде, Консалтинг), секция Проекты с превью, блок «Последние новости» с `latest_blog_post` и fallback, ссылки «Купить» на страницы товаров, «Все товары», «Все проекты», исправление «физической».
- **templates/shop.html:** фильтр «Сертификаты», карточки «Баланс-борд NewStyle» и «Сертификат на 10 занятий».

**docs/REVIEW_ARTIFACTS_AND_PROTOCOL.md** — открыть в редакторе по пути `docs/REVIEW_ARTIFACTS_AND_PROTOCOL.md` и сверять построчно (см. разделы 1–8 документа).

---

## 3. Node runtime на сервере/в контейнере и где запускается Node-сервис

**По репо:**  
Версия Node и способ запуска (pm2/systemd/docker) **в репо не заданы**. Это настраивается на стороне деплоя.

**Рекомендация:**  
В корне проекта выполнить `node -v` и прислать вывод (например, `v18.x.x` или `v20.x.x`). Для `server.js` после правок требуется **Node 18+** (используется нативный `fetch`).  
Где запускается Node-сервис (pm2/systemd/docker) — ответ даёт разработчик/инфраструктура; в коде только `package.json` → `"start": "node server.js"`.

---

## 4. Lockfile после удаления node-fetch

**Было:** В `package-lock.json` оставались зависимость `node-fetch` в корневом `""` и блок `node_modules/node-fetch`.  
**Сделано:** В рабочей копии lockfile обновлён: из корневого `packages[""].dependencies` удалён `node-fetch`, удалён блок `node_modules/node-fetch`. Файл `package-lock.json` нужно закоммитить вместе с остальными изменениями.

**Если бы не обновляли:** После `npm ci` / `npm install` в lockfile по-прежнему ставился бы `node-fetch`, а в `server.js` он уже не используется — рассинхрон между `package.json` и lockfile. Плюс при деплое лишняя зависимость. Поэтому lockfile обновлён и должен быть в коммите.

---

## 5. .gitignore: какие JSON должны остаться в репо, не сломает ли удаление *.json

**Какие JSON нужны в репо (должны оставаться отслеживаемыми):**

- **npm:** `package.json`, `package-lock.json`
- **Контент проектов:**  
  `content/projects/wsc2025/menu.json`, `meta.json`, `faq.json`, `judging_criteria.json`, `sponsor_packages.json`,  
  `content/projects/safari2026/menu.json`, `meta.json`, `partner_packages.json`
- **Данные/конфиг:** `static/data/blog_posts.json` (если используется), конфиги вроде `launch.json`, `mcp.config.json` — по решению команды
- **Тестовые/примеры:** `payload*.json`, `discovery_v1.json` — по необходимости

**Что не должно попадать в репо (уже в .gitignore):**  
`client_secret*.json`, `token.json`, `configs/service_account.json`, `instance/service_account.json` — секреты.

**Удаление правила `*.json`:**  
Раньше в `.gitignore` было правило `*.json`. Оно игнорировало **все** новые `.json` файлы; уже отслеживаемые (например, `package.json`) оставались в репо. После **удаления** `*.json` из `.gitignore`:

- Все перечисленные выше публичные JSON (package.json, контент, конфиги) могут нормально коммититься и не игнорироваться.
- Секреты по-прежнему исключены явными правилами (`client_secret*.json`, `configs/service_account.json` и т.д.).

**Вывод:** Удаление `*.json` из `.gitignore` **проект не ломает**, оно возвращает нормальное отслеживание нужных JSON в репо.

---

## 6. Staging/prod URL и конкретные шаги «какая часть сайта не видна»

**По репо:** Staging/prod URL и точные шаги воспроизведения **не заданы**. Их нужно указать разработчику.

**Что прислать (пример):**

- Staging: `https://staging.mywave.example.com` (или prod)
- Шаги: «Открыть главную → прокрутить вниз → секции Услуги / Товары / Проекты / Последние новости не видны» или «В шапке нет пунктов Товары и Проекты»
- Браузер и ширина: например, Chrome 120, 1920×1080; или Safari на iPhone

По скринам из чата: видна только верхняя часть главной (hero + кнопка «Записаться»); консоль показывает `data-modal: null` у кнопок бронирования и предупреждение `booking.js` об отсутствующих модальных элементах. То есть «не видна» может относиться к: 1) секциям ниже hero (нужна прокрутка/проверка), 2) навигации (Товары/Проекты уже добавлены в коде), 3) модалкам (пока не реализованы для товаров).

---

## 7. Видео 1–2 минуты (главная, /shop, /projects, блог, товар, с адресной строкой)

**По репо:** Видео создать и прислать может только разработчик (запись экрана браузера с адресной строкой). В репо такого артефакта нет.

---

## 8. DevTools (Console + Network) и серверные логи

**По скринам из чата (Console):**

- `booking.js`: 7 кнопок бронирования найдены, у всех `data-modal: null`; предупреждение «отсутствуют некоторые модальные элементы (это нормально, если они подгружаются позже)».
- Модули Chat, Booking, StoreFilter инициализированы как «заглушка».
- CSP Monitor инициализирован, WebSocket подключён.
- В одном из скриншотов: 3 Warnings, 1 Error (сами сообщения не видны).

**По репо:** Снимков вкладки **Network** (Doc/JS/CSS/Fetch, 404/500) и **серверных логов** (gunicorn/docker/journald) в репо нет. Их нужно снять на проблемной странице в момент загрузки и прислать разработчику.

**Рекомендация:**  
На странице, где «не видна» часть сайта: сделать полную перезагрузку (Ctrl+F5), открыть DevTools → Console (все уровни) и Network (Doc, JS, CSS, XHR), повторить шаги воспроизведения, сохранить скрин/экспорт логов Console и список запросов/ошибок в Network. С сервера — логи за тот же момент (gunicorn/docker/journald, в зависимости от того, что используется).

---

## Краткая сводка

| Запрос | Ответ |
|--------|--------|
| Ссылка на PR / ветку | Нет; правки только в рабочей копии. Нужно закоммитить список файлов выше, запушить ветку, открыть PR и прислать ссылку. |
| docs/changes.diff, REVIEW_ARTIFACTS_AND_PROTOCOL.md | Лежат в `docs/changes.diff` и `docs/REVIEW_ARTIFACTS_AND_PROTOCOL.md`. Сверять построчно по этим файлам. |
| Node runtime (node -v), pm2/systemd/docker | Из репо не следует. Нужен вывод `node -v` и ответ деплоя. Для server.js нужен Node 18+. |
| Lockfile после удаления node-fetch | Обновлён вручную в рабочей копии (package-lock.json); нужно закоммитить. Иначе расхождение с package.json и лишняя зависимость. |
| .gitignore, какие JSON в репо, не сломает ли удаление *.json | Перечислены нужные в репо JSON; секреты уже в .gitignore. Удаление `*.json` проект не ломает. |
| Staging/prod URL и шаги «что не видно» | Нужны от разработчика. |
| Видео 1–2 мин | Должен прислать разработчик. |
| DevTools Console + Network, серверные логи | По скринам: Console частично описана выше; Network и логи сервера нужно прислать с проблемной страницы. |

После появления PR/ветки, URL и артефактов (видео, Network, логи) можно отработать протокол 1→5 и обновить backlog.
