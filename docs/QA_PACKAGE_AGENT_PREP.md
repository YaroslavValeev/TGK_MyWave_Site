# Подготовка QA-пакета (сделано агентом)

**Дата:** 2026-02-03  
**Цель:** всё, что возможно сделать автоматически для Subagent E и передачи результата Ярославу.

---

## 1. Что проверено агентом

### Код (readonly)

- **`app/routes/wake_industry.py`** — редиректы 301 на каноник:
  - `GET /wake-industry` → `contest_org_checklist.checklist_page`
  - `GET /wake-industry/download` → `contest_org_checklist.download_checklist_pdf`
- **`app/__init__.py`** — blueprint чек-листа подключается опционально (`contest_org_checklist_bp` при успешном импорте), `wake_industry_bp` зарегистрирован всегда.
- **Sitemap** — в `project_slugs` для sitemap.xml указан `contest-org-checklist`.
- **Шаблоны** — в текущей ветке есть `templates/wake_industry/checklist.html`, `checklist_sections.html`, `checklist_pdf.html` (ссылки на каноник `/projects/contest-org-checklist`).

### Важно по веткам

В ветке **`fix/ux-booking-leads-store-preview`** (текущая) **нет** файла `app/routes/contest_org_checklist.py`.  
Роуты `/projects/contest-org-checklist` и `/projects/contest-org-checklist/download` реализованы в ветке **`feature/contest-org-checklist-final`** (PR #9).

**Вывод:** прогон QA по протоколу нужно выполнять:
- либо локально после `git checkout feature/contest-org-checklist-final` и запуска приложения,
- либо по ссылке на **deploy preview** PR #9 (если настроен).

Без переключения на ветку PR страница `/projects/contest-org-checklist` в текущей ветке недоступна (blueprint не зарегистрирован).

---

## 2. Протокол и артефакты

- **Протокол QA:** `docs/QA_PROTOCOL_CONTEST_ORG_CHECKLIST.md`
- **Пошаговое руководство:** `docs/STEP_BY_STEP_PR_AND_QA.md` (шаги 3–4)

**Что нужно принести Subagent E:**

| Артефакт | Статус |
|----------|--------|
| 6–10 скриншотов (страница, консоль, чекбоксы) | заполнить вручную при прогоне |
| 1 PDF с `/projects/contest-org-checklist/download` | скачать при прогоне |
| Заполненный чек-лист ОК/не ОК | заполнить по протоколу |
| (опционально) короткое видео | по желанию |

**Место размещения:** указать папку или ссылку (Google Drive, репозиторий, и т.д.) в протоколе.

---

## 3. Готовая строка для отправки Ярославу

После прогона по протоколу скопировать **один** из вариантов.

**Вариант 1 (всё ОК):**

```
QA-пакет: блокеры = 0. Проверки по docs/QA_PROTOCOL_CONTEST_ORG_CHECKLIST.md пройдены. Приложены: скриншоты, PDF, заполненный чек-лист. [ссылка на артефакты при наличии]
```

**Вариант 2 (есть блокеры):**

```
QA-пакет: обнаружены блокеры:
1. [краткое описание, например: PDF не скачивается — 500 при отсутствии WeasyPrint вместо 503]
2. [при необходимости]
Артефакты: [скриншоты/логи]. Протокол: docs/QA_PROTOCOL_CONTEST_ORG_CHECKLIST.md
```

---

## 4. Порядок действий для человека (Subagent E)

1. Переключиться на ветку PR:  
   `git fetch origin && git checkout feature/contest-org-checklist-final`
2. Запустить приложение локально (или открыть preview PR).
3. Открыть `docs/QA_PROTOCOL_CONTEST_ORG_CHECKLIST.md`.
4. Пройти все пункты A1–A6, B1–B5, C1–C2, D1–D3 и блок «Блокеры» (раздел 4 протокола).
5. Сделать скриншоты, скачать PDF, заполнить ОК/не ОК в протоколе.
6. В разделе 5 протокола отметить «Можно закрывать» или «Есть блокеры» и записать итог.
7. Отправить Ярославу: ссылку на PR (уже отправлена) + текст из п. 3 выше + ссылку на артефакты (если есть).

---

## 5. Ссылки

- PR: https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/9
- Протокол QA: `docs/QA_PROTOCOL_CONTEST_ORG_CHECKLIST.md`
- Статус и QA-гейт: `docs/CHECKLIST_STATUS_AND_QA_GATE.md`
- Что прислать Ярославу: `docs/CHECKLIST_STATUS_AND_QA_GATE.md` §4
