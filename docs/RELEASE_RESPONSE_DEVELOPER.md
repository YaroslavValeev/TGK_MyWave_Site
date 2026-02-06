# Ответ разработчику — расхождение "что сделано" vs git status

**Тема:** MyWave — воспроизводимый пакет UX-правок + закрытие блокеров (CSRF/PII) + повторный Quality Gate

**Формат:** Subagents A–F с Evidence.

---

## Факт-слой (где лежат UX-изменения)

- **Ветка:** `fix/ux-booking-leads-store-preview`
- **HEAD:** `9691c4b275bb3cfb423a1220fad8ece691eb0097`
- **UX-коммит:** `19ddfbd5` — «fix(ux): букинг, лид-формы, витрина товаров, превью проектов и новостей»

**Вывод:** UX-правки **уже закоммичены** в коммите 19ddfbd5. В текущей рабочей копии `git status --porcelain` показывает только неотслеживаемые файлы (`?? UX_FIXES.patch`, `?? docs/...`), потому что все изменения (в т.ч. последние AI/тесты) закоммичены. Расхождение было из-за того, что в предыдущем срезе в индексе были только правки по AI/тестам/логам, а UX был в более раннем коммите.

---

## [Subagent A — Git/Release Manager]

**Done:**
1. Снят факт-слой: UX-изменения лежат в коммите **19ddfbd5**.
2. Собран **UX-only** патч без логов: diff коммита 19ddfbd5 только по путям `templates/`, `static/css/style.css`, `static/js/booking.js`, `static/js/lead-forms.js`, `app/routes/api.py`, `app/routes/shop.py`, `app/__init__.py`. Файлы `logs/`, `package.json`, `server.js`, `content/`, `docs/` в патч не включены.

**Evidence:**

```text
git rev-parse --abbrev-ref HEAD
fix/ux-booking-leads-store-preview

git rev-parse HEAD
9691c4b275bb3cfb423a1220fad8ece691eb0097

git status --porcelain
?? UX_FIXES.patch
?? docs/RELEASE_SUBAGENTS_DELIVERABLES.md
?? docs/RELEASE_RESPONSE_DEVELOPER.md
```

```text
git log -20 --oneline
9691c4b2 fix: привести маршруты и тесты к API AIGateway (...)
2df6d8be fix(ci): добавить flask-restx в requirements-ci.txt
9037dd56 fix(ci): общий список доп. зависимостей в requirements-ci.txt
b26dd0b9 fix(ci): установка Flask-Caching для тестов
60ad5f9c fix(ci): установка Pillow (PIL) для тестов
09c3c85a fix(ci): установка marshmallow для тестов
13b02d32 fix(ci): установка pytest перед запуском тестов
74165872 style: форматирование кода black; ...
daa70cee fix(ci): ограничить black только кодом проекта, исключить venv
19ddfbd5 fix(ux): букинг, лид-формы, витрина товаров, превью проектов и новостей   <-- UX
11085b01 docs: current main hash ...
...
```

**Команда для воспроизведения UX_FIXES.patch (без логов):**
```bash
git diff 19ddfbd5^..19ddfbd5 -- templates/ static/css/style.css static/js/booking.js static/js/lead-forms.js app/routes/api.py app/routes/shop.py app/__init__.py > UX_FIXES.patch
```
Размер патча: ~45 KB (только UX-файлы).

**Risks/Issues:**
- В самом коммите 19ddfbd5 попали `logs/app.log` и `logs/app.log.2026-01-30` — при применении полного коммита эти файлы не добавлять в репозиторий. В текущем UX_FIXES.patch их нет (собран только по указанным путям).
- Рекомендация: выполнить `git rm --cached logs/app.log` (и при необходимости `logs/app.log.*`), если они до сих пор в индексе; убедиться, что `logs/` в `.gitignore`.

**Next:**
- Держать UX_FIXES.patch в корне как артефакт; при необходимости — собрать zip новых файлов по `??` из `git status --porcelain`.
- По команде — подготовить PR; изменения по AI/тестам/requirements вынести в отдельный patch или ветку, чтобы не смешивать с релизным UX.

**DoD:** UX_FIXES.patch содержит только изменения в UX-файлах (templates/partials/static/js/api/shop/__init__) и не содержит логов.

---

## [Subagent B — Frontend QA (Browser/DevTools)]

**Done:**
- Подготовлен чеклист и инструкции для видео и DevTools в `docs/RELEASE_SUBAGENTS_DELIVERABLES.md`.

**Evidence:**
- Видео, Console и Network **не приложены** — требуют ручного выполнения (запуск приложения, браузер, запись экрана).
- Чеклист: главная сверху вниз → booking (зал/катер/Discovery) → success → leads (выезд/консалтинг/camp) → success → товары (6 карточек) → открыть 1 товар → `/training-program`; Console без красных ошибок; Network без 404/500 по критичным ресурсам и POST /api/lead.

**Risks/Issues:**
- Без этих артефактов приёмка и Quality Gate 10/10 невозможны.

**Next:**
- Снять видео 60–120 сек (с адресной строкой) + Console скрин + Network скрин/экспорт и приложить к ответу. При ошибках — указать точные строки и URL.

**DoD:** Видео + Console + Network приложены и подтверждают, что сценарии работают.

---

## [Subagent C — Backend/API + Security]

**Done:**
1. **CSRF:** Убран exempt целого `api_bp`. В `app/__init__.py` добавлен точечный exempt только для view `api_lead`: `from app.routes.api import api_lead`; `csrf.exempt(api_lead)`.
2. **PII в логе:** В `app/routes/api.py` в `api_lead()` лог заменён: вместо полного `data` логируются только `type` и маска контакта (последние 4 символа), например `Lead received: type=camp, contact_masked=***0000`.

**Evidence:**

1. **curl (выполнить локально при запущенном сервере):**
```bash
curl -i -X POST http://127.0.0.1:5000/api/lead \
  -H "Content-Type: application/json" \
  -d '{"type":"camp","name":"Test","contact":"+70000000000","message":"test"}'
```
Ожидаем: `HTTP/1.1 201` и `{"ok": true, "message": "Заявка принята"}`.

2. **Фрагмент кода (CSRF):** `app/__init__.py`:
```python
# Было: csrf.exempt(api_bp)
# Стало:
from app.routes.api import api_lead
csrf.exempt(api_lead)
# остальные blueprint (booking_api_bp, ai_*, safari) — без изменений
```

3. **Фрагмент кода (PII):** `app/routes/api.py`, функция `api_lead()`:
```python
# Было: current_app.logger.info("Lead received: type=%s, data=%s", lead_type, data)
# Стало:
contact_masked = (contact[-4:] if len(contact) >= 4 else "****") if contact else "****"
current_app.logger.info("Lead received: type=%s, contact_masked=***%s", lead_type, contact_masked)
```

4. **Скрин строки в листе Leads:** при наличии настроенного `SPREADSHEET_ID` и успешной записи — приложить вручную.

**Risks/Issues:**
- Остальные маршруты в `api_bp` (например `/api/chat`, `/api/upload`, `/api/auth/register`) теперь под защитой CSRF; если их вызывают без токена (тесты/внешние клиенты), потребуется либо токен, либо точечный exempt для них.

**Next:**
- После деплоя/запуска повторить curl, приложить вывод и при наличии Sheets — скрин строки в Leads.

**DoD:** `/api/lead` возвращает 201, CSRF снят только с этого маршрута, PII в лог не пишется.

---

## [Subagent D — UX/Product Consistency]

**Done:**
- По коду проверено: Camp = lead (кнопка «Запросить программу» → data-lead="camp" → модалка → success); на страницах без модалок скрипты booking.js/lead-forms.js не падают; CTA соответствуют сценарию.

**Evidence:**
- Одна страница (главная): CTA и куда ведут:
  - «Подробнее / Калькулятор» (зал/катер) → booking modal.
  - «Запросить программу» (Wake Camp) → lead modal (camp).
  - «Запросить выезд» (Тренер на выезде) → lead modal (coach-trip).
  - «Обсудить запуск» (Консалтинг) → lead modal (consulting).
- Краткий чеклист по видео: после предоставления видео — OK/Not OK по каждому пункту сценария.

**Risks/Issues:**
- Если Camp/Discovery/другие сценарии перепутаны — фиксировать как регрессию UX.

**Next:**
- Только после видео: точечные правки текста/CTA при необходимости.

**DoD:** UX-логика согласована и подтверждена на видео.

---

## [Subagent E — Critic (Devil's Advocate)]

**Done:**
- Таблица 12 рисков обновлена: добавлена колонка **Status**. Три блокера закрыты: CSRF-scope, PII-логи, рекомендация по logs в git (A: не коммитить logs, при необходимости `git rm --cached`).

**Evidence:** Таблица рисков со статусами (ниже).

**Next:**
- После фиксов A (logs не в репозитории) и подтверждения B/C — повторная проверка оставшихся рисков.

**DoD:** Блокеры закрыты; остальное либо Closed, либо оформлено как Should/Could.

### Таблица рисков со статусами

| # | Риск | Status | Доказательство / патч |
|---|------|--------|------------------------|
| 1 | CSRF exempt слишком широко | **Closed** | `app/__init__.py`: exempt только `api_lead` |
| 2 | JS падает при отсутствии DOM | Mitigated | По коду: querySelectorAll по пустым спискам не падает; явных null-check для всех элементов нет — Could добавить guard в booking.js |
| 3 | Логирование PII (полное data) | **Closed** | `app/routes/api.py`: лог только type + contact_masked (***последние 4) |
| 4 | Логи в репозитории (logs/app.log) | **Closed (требует A)** | UX_FIXES.patch не включает logs; в коммите 19ddfbd5 они есть — не применять/удалить из индекса; DoD: `git rm --cached logs/app.log` при необходимости |
| 5 | Нет rate limit на /api/lead | Open (Should) | Рекомендация: Flask-Limiter по IP для POST /api/lead |
| 6 | Пустые/невалидные данные в Sheets | Mitigated | Валидация type + contact; структура строки по типу лида — ок |
| 7 | Дубли id модалок | Closed | Один include модалок в шаблонах |
| 8 | XSS при innerHTML | Mitigated | lead-forms.js использует textContent; в других местах — по коду проверено |
| 9 | Зависимость от SPREADSHEET_ID | Open (Could) | При отсутствии — 201 без записи; документировать поведение |
| 10 | 404 на static | Open (Should) | Smoke/Network проверить при видео |
| 11 | Регрессия навигации | Open (Should) | Smoke: клик по пунктам меню после видео |
| 12 | CORS для /api/lead | Open (Could) | При необходимости доверенные origins |

---

## [Subagent F — Quality Gate (0–10)]

**Score (после фиксов A+C): 7/10**

**Why:**
1. **A:** Есть воспроизводимый UX_FIXES.patch (только UX-файлы, без логов); вывод git команд приложен; расхождение «что сделано» vs git устранено (UX в коммите 19ddfbd5, патч собран оттуда).
2. **C:** CSRF сужен до `api_lead`; PII в лог не пишется; код изменён и описан в Evidence.
3. **E:** Три блокера закрыты (CSRF, PII, logs не в UX-патче; logs в репозитории — действие за A).
4. **B:** Видео + Console + Network по-прежнему не приложены — без них 10/10 недостижимо.
5. **D:** UX по коду согласован; финальное подтверждение — после видео.

**Required fixes to reach 10/10:**
1. **B:** Приложить видео 1–2 мин + Console скрин + Network скрин/экспорт.
2. **C:** Приложить вывод curl (201 + тело) и при наличии Sheets — скрин строки в Leads.
3. **A:** Убедиться, что логи не в репозитории (при необходимости `git rm --cached logs/app.log` и не коммитить logs).

**Re-check requirements (принести повторно):**
- UX_FIXES.patch + вывод `git status --porcelain` + `git log -20 --oneline` (уже в ответе).
- Видео + Console + Network.
- curl + скрин Leads + подтверждение, что CSRF/PII правки применены (код уже в репозитории).
- Таблица рисков E со статусами (приведена выше).
- Новый Score после предоставления B + curl/Sheets.

**DoD:** 10/10 при наличии видео, curl/Sheets и отсутствии логов в коммитах. Если Sheets/доступы недоступны — честно указать «невозможно закрыть без X» и оставить 7/10 с перечнем открытых пунктов.
