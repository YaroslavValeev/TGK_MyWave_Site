# Пошаговое руководство: PR + QA для чек-листа организатора

**Дата:** 2026-02-03  
**Ветка:** `feature/contest-org-checklist-final` → `main`

---

## ✅ Что уже сделано автоматически

- ✅ Ветка `feature/contest-org-checklist-final` создана от `main`
- ✅ Коммит содержит только файлы чек-листа (11 файлов, 1121 строка добавлено)
- ✅ Конфликт-маркеры проверены — не найдены
- ✅ Документация обновлена (`PR_CONTEST_ORG_CHECKLIST.md`, `SUBAGENTS_ASSIGNMENT_AND_SKILLS.md`)

**Статус ветки:** ✅ запушена в `origin/feature/contest-org-checklist-final` (готово к созданию PR).

---

## 📋 Шаг 1: Push ветки в origin (Subagent A)

### Команды для выполнения:

```bash
# Переключиться на ветку чек-листа
git checkout feature/contest-org-checklist-final

# Запушить ветку в origin
git push -u origin feature/contest-org-checklist-final
```

**Проверка:** после выполнения команды `git ls-remote --heads origin feature/contest-org-checklist-final` должна вернуть хеш коммита.

**Если возникла ошибка доступа:** убедитесь, что у вас есть права на push в репозиторий. Если ветка уже существует удалённо с другим содержимым — используйте `git push --force-with-lease origin feature/contest-org-checklist-final` (осторожно!).

---

## 📋 Шаг 2: Создать PR в веб-интерфейсе (Subagent A)

### Действия:

1. **Открыть репозиторий** в GitHub/GitLab/Bitbucket (в зависимости от вашего хостинга).

2. **Перейти в раздел Pull Requests** (или Merge Requests в GitLab).

3. **Нажать "New Pull Request"** (или "Create Merge Request").

4. **Выбрать ветки:**
   - **Base:** `main` (или `master`, если у вас master)
   - **Compare:** `feature/contest-org-checklist-final`

5. **Заполнить заголовок PR:**
   ```
   feat(projects): чек-лист организатора — каноник /projects/contest-org-checklist, редиректы, PDF, изоляция print-стилей
   ```

6. **Вставить описание из `docs/PR_CONTEST_ORG_CHECKLIST.md`** (разделы "Что сделано", "Файлы в диффе", "DoD", "QA").

7. **Проверить diff:**
   - Убедиться, что в diff только файлы чек-листа (11 файлов).
   - Проверить, что нет изменений в `app/routes/api.py`, `app/routes/chat.py`, `app/routes/services.py`, `app/routes/shop.py` и других файлах вне чек-листа.

8. **Создать PR** (Create Pull Request / Create Merge Request).

9. **Скопировать ссылку на PR** и отправить Ярославу.

---

## 📋 Шаг 3: QA-проверка по протоколу (Subagent E)

### Подготовка:

1. **Развернуть ветку локально** (если ещё не сделано):
   ```bash
   git checkout feature/contest-org-checklist-final
   # Запустить приложение локально
   ```

2. **Открыть протокол QA:** `docs/QA_PROTOCOL_CONTEST_ORG_CHECKLIST.md`

### Чек-лист QA (кратко):

#### A) HTML-страница

- [ ] Открывается `/projects/contest-org-checklist` без 500/404
- [ ] Нет ошибок в консоли браузера (F12 → Console)
- [ ] Структура секций 1–10 совпадает с эталоном
- [ ] Чекбоксы работают и сохраняются (localStorage)
- [ ] Изображения подгружаются (если должны быть)
- [ ] CSP: нет блокировок критичных скриптов/стилей

#### B) PDF-генерация

- [ ] `/projects/contest-org-checklist/download` скачивается и открывается
- [ ] PDF по структуре соответствует эталону (секции, заголовки, переносы)
- [ ] Картинки (если есть) корректно резолвятся
- [ ] **Сценарий 1:** WeasyPrint установлен → PDF скачивается
- [ ] **Сценарий 2:** WeasyPrint отсутствует → показывается понятная страница (503) с альтернативой «печать из браузера»

#### C) Редиректы

- [ ] `/wake-industry` → `/projects/contest-org-checklist` (301)
- [ ] `/wake-industry/download` → `/projects/contest-org-checklist/download` (301)

#### D) SEO

- [ ] canonical указывает на канонический URL проекта
- [ ] title/description адекватны
- [ ] OG/Twitter теги корректны

#### E) Print-изоляция (Subagent D)

- [ ] Печать **другой страницы** (например, главной) — шапка/подвал не пропадают
- [ ] Печать **страницы чек-листа** — только контент без навигации/кнопок

### Артефакты QA-пакета (что собрать):

1. **6–10 скриншотов:**
   - Страница `/projects/contest-org-checklist` (верх, середина, низ)
   - Консоль браузера без ошибок (F12 → Console)
   - Чекбоксы в действии
   - Редиректы (Network tab → проверить статус 301)
   - Печать другой страницы (чтобы показать, что не сломалась)
   - Печать страницы чек-листа (чтобы показать изоляцию)

2. **1 итоговый PDF:**
   - Скачать по `/projects/contest-org-checklist/download`
   - Сохранить файл как `chek-list-organizatora-sorevnovanij.pdf`

3. **Заполненный чек-лист:**
   - Открыть `docs/QA_PROTOCOL_CONTEST_ORG_CHECKLIST.md`
   - Заполнить таблицы "ОК / не ОК" для каждого критерия
   - При "не ОК" — указать причину в колонке "Комментарий"

4. **(Опционально) Короткое видео:**
   - Открыть страницу → нажать download PDF → открыть PDF
   - Длительность: 30–60 секунд
   - Формат: MP4 или GIF

---

## 📋 Шаг 4: Вердикт одной строкой

После завершения QA заполнить и отправить Ярославу:

**Вариант 1 (всё ОК):**
```
блокеры = 0
```

**Вариант 2 (есть блокеры):**
```
блокеры: [список проблем, например: "PDF не генерируется при отсутствии WeasyPrint (показывает 500 вместо 503)", "Редирект /wake-industry возвращает 404"]
```

---

## 📋 Шаг 5: Подготовка файлов Wake Challenge (только если "блокеры = 0")

После получения вердикта "блокеры = 0" — подготовить пакет файлов по `docs/WAKE_CHALLENGE_FILES_FOR_PATCH_PLAN.md`.

### Что собрать:

1. **Содержимое ключевых файлов:**
   - `templates/projects/wsc2025.html` (целиком или фрагменты HERO, секции)
   - `static/projects/wsc2025/styles.css` (особенно HERO)
   - Фрагменты `app/routes/projects/wakesurf_challenge.py` (формирование meta, canonical)
   - `configs/showcases/wsc_2026.yaml` (уже есть в репозитории)
   - При наличии: `content/projects/wsc2025/index.md`, `menu.json`, `meta.json`

2. **Отправить Ярославу** для точечного патч-плана.

---

## ✅ Итоговый чек-лист отправки Ярославу

Перед отправкой убедиться, что есть:

- [ ] **Ссылка на PR** `feature/contest-org-checklist-final` → `main`
- [ ] **QA-пакет:**
  - [ ] 6–10 скриншотов
  - [ ] 1 итоговый PDF
  - [ ] Заполненный чек-лист ОК/не ОК
  - [ ] (Опционально) видео
- [ ] **Строка-вердикт:** "блокеры = 0" или список блокеров
- [ ] **(Если блокеры = 0) Файлы Wake Challenge** по `WAKE_CHALLENGE_FILES_FOR_PATCH_PLAN.md`

---

## 🔧 Troubleshooting

### Проблема: ветка не пушится

**Решение:**
```bash
# Проверить, что вы на правильной ветке
git branch

# Проверить статус
git status

# Если есть конфликты с удалённой веткой
git fetch origin
git rebase origin/main  # или git merge origin/main
git push -u origin feature/contest-org-checklist-final
```

### Проблема: в diff PR видны лишние файлы

**Решение:**
- Убедиться, что base branch — `main` (не другая ветка)
- Проверить, что в коммите `151217c1` только нужные файлы: `git show 151217c1 --stat`
- Если в PR попали изменения из других веток — пересоздать ветку от актуального `main`

### Проблема: PDF не генерируется

**Проверка:**
```bash
# Проверить, установлен ли WeasyPrint
pip list | grep -i weasy

# Если нет — установить (для тестирования)
pip install weasyprint
```

**Ожидаемое поведение:**
- Если WeasyPrint установлен → PDF скачивается
- Если WeasyPrint отсутствует → показывается страница 503 (`pdf_unavailable.html`)

---

## 📞 Контакты для вопросов

Если возникли вопросы по процессу — обратиться к Ярославу или к lead-разработчику.

---

**Последнее обновление:** 2026-02-03
