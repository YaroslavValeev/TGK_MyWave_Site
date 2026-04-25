# Раздел «Проекты» — карта, аудит и план приведения к карточной логике

**Дата:** 2025-03-19  
**Обновлено:** реализована консолидация Checklist, исправлена опечатка  
**Scope:** только раздел «Проекты», без Services / Shop / главной

---

## 1. Карта раздела — таблица по всем проектам

| Проект | id | slug | YAML | Partial карточки | URL кнопки «Подробнее» | Фактический route | Поведение |
|--------|-----|------|------|------------------|------------------------|-------------------|-----------|
| **WakeSurf Challenge** | wake_challenge | wake-challenge | wake_challenge.yaml | project_card_wake_challenge.html | /projects/wakesurf-challenge-2025 | wakesurf_challenge_bp | ✅ Отдельная страница |
| **WakeSurf Safari** | wakesurf_safari | wakesurf-safari | wakesurf_safari.yaml | project_card_wakesurf_safari.html | /projects/wakesurf-safari | projects_safari_bp | ✅ Отдельная страница |
| **Чек-лист организатора** | checklist | checklist-org | contest_org_checklist.yaml | project_card_checklist.html | /projects/checklist-org | project_detail → checklist.html | ✅ Отдельная страница |
| **MyWave Ruza Camp** | mywave_ruza_camp | mywave-ruza-camp | mywave_ruza_camp.yaml | project_card_ruza_camp.html | /projects/mywave-ruza-camp | project_detail → ruza_camp.html | ✅ Отдельная страница |
| **Wake Industry** | wake_industry | wake-industry | wake_industry.yaml | — | — | channels: [] | Убран с витрины (консолидирован) |

**Задействованные файлы:**
- `configs/showcases/`: wake_challenge.yaml, wakesurf_safari.yaml, contest_org_checklist.yaml, mywave_ruza_camp.yaml, wake_indusrty.yaml
- `app/services/showcases.py`: get_project_cards(), _PROJECT_ORDER
- `app/__init__.py`: projects_page(), project_detail()
- `app/routes/projects_safari.py`, `app/routes/projects/wakesurf_challenge.py`, `app/routes/wake_industry.py`
- `templates/partials/project_card*.html`, `templates/projects/*.html`, `templates/wake_industry/checklist.html`

**Примечание:** sochi_camp в channels: events, на витрине /projects не участвует.

---

## 2. Что проблемно сейчас

### 2.1 Маршруты
- **Wake Industry** — карточка ведёт на `/projects/wake-indusrty` → редирект на `/projects#wake-indusrty` (якорь). Отдельной страницы нет.
- **Checklist** — ведёт на `/wake-industry` (вне пространства /projects). Маршрут `/projects/checklist-org` редиректит на `/wake-industry` — несогласованность с префиксом /projects.
- **Legacy:** `/projects/wake-challenge` → 301 на `/projects/wakesurf-challenge-2025` — корректно.

### 2.2 Slug / naming
- **wake_indusrty** — опечатка (должно быть wake_industry). Затрагивает: id в YAML, _PROJECT_ORDER, логику get_project_cards.
- **Конфликт имён:** страница `/wake-industry` называется «Индустрия вейка — Чеклист условий для соревнований», но по смыслу это страница **Checklist** (чек-лист организатора), а не «Wake Industry» (индустрия в целом).

### 2.3 Карточки
- Checklist и Wake Industry используют generic `project_card.html` — корректно, но контент разный.
- Checklist ведёт на /wake-industry — страница чеклиста есть.
- Wake Industry ведёт в якорь — страницы нет.

### 2.4 Страницы
- **WakeSurf Challenge** — `projects/wsc2025.html` ✅
- **WakeSurf Safari** — `projects/safari.html` ✅
- **MyWave Ruza Camp** — `projects/ruza_camp.html` ✅
- **Checklist** — `wake_industry/checklist.html` (URL /wake-industry) ✅
- **Wake Industry** — страницы нет ❌

### 2.5 Checklist vs Wake Industry — смысловая путаница

| Аспект | Checklist | Wake Industry |
|--------|-----------|---------------|
| **YAML** | «Чек-лист для организатора» — провести соревнование без хаоса | «Индустрия вейксерфинга: оборудование, события, партнёры» |
| **Контент страницы /wake-industry** | Подробный чеклист: судьи, безопасность, документы и т.д. | Тот же контент (checklist) |
| **Вывод** | Checklist = практический инструмент организатора | Wake Industry = обзор индустрии (другой фокус) |

**Проблема:** страница `/wake-industry` по сути — страница **Checklist**. Название «Индустрия вейка» на странице создаёт путаницу с карточкой «Wake Industry», которая описывает индустрию в целом.

**Варианты:**
1. **Развести:** Checklist → своя страница (чеклист), Wake Industry → своя страница (обзор индустрии, контент нужно создать).
2. **Объединить:** считать Checklist и Wake Industry одним проектом «Чек-лист для организатора / Индустрия вейка», убрать дублирующую карточку, оставить одну страницу.

---

## 3. Предлагаемое решение

### 3.1 По каждому проекту

| Проект | Решение |
|--------|---------|
| **WakeSurf Challenge** | Оставить как есть |
| **WakeSurf Safari** | Оставить как есть |
| **MyWave Ruza Camp** | Оставить как есть |
| **Checklist** | Нормализовать: canonical URL `/projects/checklist-org`, страница checklist. Редирект /wake-industry → /projects/checklist-org для backward compatibility. |
| **Wake Industry** | **Требует решения владельца** — см. раздел 5 |

### 3.2 Checklist и Wake Industry — рекомендация

**Рекомендация: консолидация.**

Причины:
- Страница `/wake-industry` содержит только чеклист организатора.
- Контента «оборудование, события, партнёры» нет и не планировался.
- Две карточки с разными названиями ведут к одному типу контента (чеклист).

**Предлагаемая консолидация:**
1. Оставить одну карточку **«Чек-лист для организатора»** (Checklist).
2. Убрать карточку **«Wake Industry»** из витрины проектов (или скрыть через channels).
3. Canonical URL чеклиста: `/projects/checklist-org`.
4. Маршрут: project_detail или отдельный route рендерит `wake_industry/checklist.html`.
5. Legacy: `/wake-industry` → 301 на `/projects/checklist-org`.

**Альтернатива (если Wake Industry — отдельный продукт):**
- Создать страницу Wake Industry с контентом «оборудование, события, партнёры» (landing/обзор).
- Canonical URL: `/projects/wake-industry`.
- Исправить опечатку wake_indusrty → wake_industry.

---

## 4. План реализации

### Шаг 1. Решение по Checklist и Wake Industry (от владельца)
- Консолидировать (одна карточка) или развести (две страницы)?

### Шаг 2. Нормализация маршрутов (минимальные изменения)

**Если консолидация:**
1. `showcases.py`: убрать wake_indusrty из _PROJECT_ORDER или убрать из channels: projects.
2. `showcases.py`: checklist card url = `/projects/checklist-org`.
3. `__init__.py` project_detail: slug `checklist-org` → render `wake_industry/checklist.html` (или переименовать шаблон).
4. Добавить route `/projects/checklist-org` — рендер checklist-страницы.
5. Добавить redirect `/wake-industry` → `/projects/checklist-org` (301).
6. Убрать redirect `checklist-org` → `/wake-industry`.

**Если разведение:**
1. Создать `templates/projects/wake_industry.html` — страница «Индустрия вейксерфинга».
2. Добавить route `/projects/wake-industry` (исправить slug в YAML).
3. Исправить wake_indusrty → wake_industry в YAML и коде.

### Шаг 3. Исправление опечатки wake_indusrty (если Wake Industry остаётся)
- Переименовать в YAML: id, slug.
- Обновить _PROJECT_ORDER.
- Backward compatibility: redirect `/projects/wake-indusrty` → `/projects/wake-industry`.

### Шаг 4. Единая схема «карточка → страница»
- Все карточки: url = `/projects/{canonical-slug}`.
- Все slug-и ведут на отдельную страницу, не на якорь.
- project_detail: убрать fallback `redirect(url_for('projects_page', _anchor=slug))` для проектов из витрины — каждый должен иметь явный route.

### Шаг 5. Sitemap
- Добавить project_slugs в sitemap для индексации страниц проектов.

---

## 5. Что нужно от владельца

### 5.1 Checklist и Wake Industry
**Вопрос:** Это один проект или два?

- **Один проект (консолидация):** «Чек-лист для организатора» — единственная карточка, страница с чеклистом. Wake Industry убрать из витрины.
- **Два проекта (разведение):** Нужна отдельная страница для «Wake Industry» (индустрия: оборудование, события, партнёры). Контент для неё нужно будет подготовить.

### 5.2 Canonical URL для чеклиста
**Вопрос:** Где должен жить чеклист?

- **Вариант A:** `/projects/checklist-org` (в пространстве проектов).
- **Вариант B:** `/wake-industry` (текущий URL, оставить).

### 5.3 Опечатка wake_indusrty
**Вопрос:** Исправлять ли на wake_industry? Затронет YAML, код, возможные закладки.

---

## 6. Текущее состояние страниц проектов (этап 2: визуально раскрытые)

| Проект | Страница | Статус |
|--------|----------|--------|
| WakeSurf Challenge | projects/wsc2025.html | ✅ Hero, subnav, карточки, timeline, CTA |
| WakeSurf Safari | projects/safari.html | ✅ Hero, subnav, unique grid, маршрут, FAQ, CTA |
| MyWave Ruza Camp | projects/ruza_camp.html | ✅ Hero, mw-card блоки, FAQ, CTA |
| Чек-лист организатора | wake_industry/checklist.html | ✅ Hero (без legacy naming), Что это, Ценность, Как устроен, CTA, чеклист |
| Wake Industry | — | Убран с витрины (консолидирован) |

---

## 7. Self-QA чек-лист (после реализации)

- [ ] Все 4–5 карточек на /projects ведут на отдельную страницу.
- [ ] Нет переходов на якорь как основной сценарий.
- [ ] Кнопка «Подробнее» у всех работает одинаково.
- [ ] Wake Industry приведён к логическому состоянию (страница или скрыт).
- [ ] Checklist и Wake Industry не конфликтуют.
- [ ] Canonical URL согласованы с YAML и routes.
- [ ] Legacy redirects работают.
