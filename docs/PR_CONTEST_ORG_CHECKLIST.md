# PR: Чек-лист организатора соревнований (чистая ветка)

**Ветка:** `feature/contest-org-checklist-final` → `main`  
**Дата:** 2026-02-03

---

## Заголовок PR (Title)

```
feat(projects): чек-лист организатора — каноник /projects/contest-org-checklist, редиректы, PDF, изоляция print-стилей
```

---

## Описание PR (Description)

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

- [ ] В PR нет правок, не относящихся к чек-листу (услуги/магазин/чат/аналитика/главная/другие проекты).
- [ ] Страница `/projects/contest-org-checklist` открывается без ошибок.
- [ ] Редиректы 301 работают.
- [ ] PDF скачивается по `/projects/contest-org-checklist/download` (или показывается 503 при отсутствии WeasyPrint).
- [ ] Print-изоляция: печать другой страницы не меняется; на странице чек-листа при печати — только контент без шапки/кнопок.

### QA

- Прогон по протоколу: `docs/QA_PROTOCOL_CONTEST_ORG_CHECKLIST.md`.
- После мержа ожидается пакет: скриншоты, PDF, заполненный чек-лист ОК/не ОК, строка «блокеры = 0».

---

## Чек-лист перед мержем

- [ ] Ветка создана от актуального `main`.
- [ ] В коммите только перечисленные выше файлы.
- [ ] Локально проверены: открытие страницы, редиректы, скачивание PDF (или 503).
- [ ] CI (если есть) зелёный.
- [ ] QA-пакет от Subagent E приложен/зафиксирован (до или после мержа по процессу).

---

## Ссылка на PR

*(вставить после создания)*
