# План по завершению задач по бэкенду

**Дата:** 2026-02-03  
**Источник:** `docs/BACKEND_TODO_AFTER_CHECKLIST.md`, порядок из `docs/SUBAGENTS_ASSIGNMENT_AND_SKILLS.md`.

---

## 0. Правило скоупа

Работаем строго в рамках: **Чек-лист** → **Wake Challenge** → **WakeSurf Safari** → **Раздел «Проекты»**.  
Никаких попутных правок главной/услуг/магазина/чата/аналитики вне этих направлений.

---

## 1. Порядок закрытия направлений

| # | Направление | Условие старта | Бэкенд-задачи | Статус |
|---|-------------|----------------|---------------|--------|
| 1 | Чек-лист организатора | — | PR + QA + «блокеры = 0» + merge | Ожидает QA |
| 2 | Wake Challenge (WSC) | После мержа чек-листа | Пакет файлов → патч-план Ярослава → CTA/табы/CSRF, canonical/meta | Ожидает пакета |
| 3 | WakeSurf Safari | После WSC | Эндпоинты под лид-форму при необходимости; canonical/meta страницы Safari | После WSC |
| 4 | Раздел «Проекты» | После WSC → Safari | Расширить источник данных: `gallery[]`, `modal_content`, `primary_actions[]`, `page_url` | **Подготовка данных выполнена** |

---

## 2. Что сделано в рамках плана (реализация)

### 2.1 Раздел «Проекты» — бэкенд данных витрины

**Задача из BACKEND_TODO_AFTER_CHECKLIST п.3:** расширить источник данных (YAML/сервис) под фронт.

**Выполнено:**

- В **`app/services/showcases.py`**:
  - В `ShowcaseConfig` добавлены поля: `modal_content` (str | None), `primary_actions` (list[dict]), `page_url` (str | None).
  - В `as_card()` в карточку передаются: `modal_content`, `primary_actions`, `page_url` (fallback на `url` при отсутствии `page_url`).
  - Галерея уже была (`gallery` → `images` в карточке); рекомендация: минимум 3 изображения заполнять в YAML по мере появления контента.

- В **`configs/showcases/`**:
  - В примеры конфигов добавлены (где релевантно) поля `modal_content`, `primary_actions`, `page_url` для совместимости с модалкой и CTA (см. спецификацию `docs/PROJECTS_UX_SPEC_AND_DOD.md`).

**Итог:** главная и `/projects` по-прежнему рендерят один список через `get_project_cards()` / `get_project_cards_preview()`; фронт (карусель, модалка, галерея) сможет использовать новые поля без доработки бэкенда на этапе реализации раздела «Проекты».

### 2.2 Wake Challenge — canonical в meta

**Задача:** canonical и meta на канонический домен (mywavetreaning.ru).

**Выполнено:**

- В **`app/routes/projects/wakesurf_challenge.py`** дефолтный `meta` при отсутствии `content/projects/wsc2025/meta.json` приведён к домену **mywavetreaning.ru** (вместо mywavetraining.ru).
- Файл **`content/projects/wsc2025/meta.json`** уже содержит корректный домен; правка в коде страхует от регресса при отсутствии файла.

### 2.3 Wake Challenge — что остаётся после патч-плана

- Починить неработающие CTA/табы/submit (в т.ч. 400/CSRF) — по точечному патч-плану от Ярослава.
- Корректные сценарии по ролям (участник/тренер/спонсор).
- Пакет файлов для патч-плана: `docs/WAKE_CHALLENGE_FILES_FOR_PATCH_PLAN.md`.

### 2.4 WakeSurf Safari

- Canonical/meta для страницы Safari — проверить при спринте Safari; при необходимости отдавать с бэкенда.
- Расширение эндпоинтов под лид-форму и партнёрские интеграции — по требованию спринта.

---

## 3. Чек-лист «сделано / осталось»

- [x] План задокументирован (`docs/BACKEND_PLAN_AND_IMPLEMENTATION.md`).
- [x] ShowcaseConfig и as_card() расширены полями для раздела «Проекты» (modal_content, primary_actions, page_url).
- [x] Примеры в YAML витрины обновлены (поля для модалки/CTA).
- [x] WSC: дефолтный meta в коде с canonical на mywavetreaning.ru.
- [ ] Чек-лист: QA-пакет + «блокеры = 0» + merge (ответственный: Subagent E, Ярослав).
- [ ] WSC: пакет файлов по `WAKE_CHALLENGE_FILES_FOR_PATCH_PLAN.md` → патч-план → спринт DoD 10/10.
- [ ] Safari: спринт после WSC; canonical/meta и эндпоинты по необходимости.
- [ ] Проекты: фронт (карусель, модалка, галерея) по `docs/PROJECTS_UX_SPEC_AND_DOD.md` после WSC и Safari.

---

## 4. Ссылки

- Бэкенд-хвосты: `docs/BACKEND_TODO_AFTER_CHECKLIST.md`
- Спецификация «Проекты»: `docs/PROJECTS_UX_SPEC_AND_DOD.md`
- Wake Challenge: `docs/WAKECHALLENGE_REQUIREMENTS.md`, `docs/WAKE_CHALLENGE_FILES_FOR_PATCH_PLAN.md`
- Safari: `docs/SAFARI_REQUIREMENTS.md`
- QA-гейт чек-листа: `docs/CHECKLIST_STATUS_AND_QA_GATE.md`
