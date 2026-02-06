# Описание PR — готово к копированию

**Ссылка на создание PR:** https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/new/feature/contest-org-checklist-final

---

## Заголовок PR (Title)

```
feat(projects): чек-лист организатора — каноник /projects/contest-org-checklist, редиректы, PDF, изоляция print-стилей
```

---

## Описание PR (Description) — скопировать всё ниже

### Что сделано

- **Канонические URL:** страница `/projects/contest-org-checklist`, скачивание PDF `/projects/contest-org-checklist/download`.
- **Редиректы 301:** `/wake-industry` → `/projects/contest-org-checklist`, `/wake-industry/download` → `/projects/contest-org-checklist/download`.
- **Новая структура шаблонов:** `templates/projects/contest_org_checklist/` (checklist.html, checklist_pdf.html, pdf_error.html, pdf_unavailable.html, _checklist_content.html).
- **Обработка ошибок PDF:** при отсутствии WeasyPrint возвращается 503 и понятная HTML-страница; при ошибке генерации — страница с описанием ошибки (500).
- **Изоляция print-стилей:** в `base.html` добавлен блок `body_class`; на странице чек-листа задаётся класс `project--contest-org-checklist`; в `style.css` все print-правила привязаны к `body.project--contest-org-checklist` (печать других страниц не затрагивается).
- **Конфиг витрины:** `configs/showcases/contest_org_checklist.yaml`.

### Файлы в диффе (только чек-лист)

| Файл | Изменение |
|------|-----------|
| `app/__init__.py` | Импорт и регистрация `wake_industry_bp`, `contest_org_checklist_bp` |
| `app/routes/contest_org_checklist.py` | Новый blueprint: страница + download PDF |
| `app/routes/wake_industry.py` | Только 301 редиректы на каноник |
| `templates/base.html` | Блок `{% block body_class %}` в `<body>` |
| `templates/projects/contest_org_checklist/*` | Все шаблоны страницы и PDF |
| `static/css/style.css` | Блок `@media print` для `body.project--contest-org-checklist` |
| `configs/showcases/contest_org_checklist.yaml` | Карточка на витрине проектов |

### DoD (Definition of Done)

- [x] В PR нет правок, не относящихся к чек-листу (услуги/магазин/чат/аналитика/главная/другие проекты).
- [ ] Страница `/projects/contest-org-checklist` открывается без ошибок.
- [ ] Редиректы 301 работают.
- [ ] PDF скачивается по `/projects/contest-org-checklist/download` (или показывается 503 при отсутствии WeasyPrint).
- [ ] Print-изоляция: печать другой страницы не меняется; на странице чек-листа при печати — только контент без шапки/кнопок.

### QA

- Прогон по протоколу: `docs/QA_PROTOCOL_CONTEST_ORG_CHECKLIST.md`.
- После мержа ожидается пакет: скриншоты, PDF, заполненный чек-лист ОК/не ОК, строка «блокеры = 0».

---

## Инструкция по созданию PR

1. **Открыть ссылку:** https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/new/feature/contest-org-checklist-final

2. **Проверить ветки:**
   - Base: `main` (или `master`)
   - Compare: `feature/contest-org-checklist-final`

3. **Вставить заголовок** (см. выше)

4. **Вставить описание** (скопировать весь блок "Описание PR" выше)

5. **Проверить diff:**
   - В diff только файлы чек-листа: `app/__init__.py`, `app/routes/contest_org_checklist.py`, `app/routes/wake_industry.py`, `templates/base.html`, `templates/projects/contest_org_checklist/*`, `static/css/style.css`, `configs/showcases/contest_org_checklist.yaml`, документы (по списку в `docs/SUBAGENTS_ASSIGNMENT_AND_SKILLS.md`, п. 3).
   - Не должно быть изменений в `app/routes/api.py`, `app/routes/chat.py`, `app/routes/services.py`, `app/routes/shop.py` и других файлах вне чек-листа.

6. **Создать PR** (Create Pull Request)

7. **Скопировать ссылку на созданный PR** и отправить Ярославу

---

**Последнее обновление:** 2026-02-03
