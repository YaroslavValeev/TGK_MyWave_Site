# Чек-лист организатора соревнований — матрица subagents и статус

## Источник истины (эталон)

- **Эталон:** «Чек-лист Организатора — Условия для соревнований по вейксерфингу» (HTML/PDF).
- **Правило:** страница и PDF должны визуально и структурно соответствовать эталону, адаптируясь под layout сайта.

---

## Матрица subagents (роль → задачи → skills)

| Subagent | Роль | Задачи | Skills |
|----------|------|--------|--------|
| **A** | Архитектор (Routing & Slugs) | Развести маршруты contest-org-checklist ≠ wake-industry; URL `/projects/<slug>`; редирект /wake-industry → /projects/contest-org-checklist; проверить YAML витрины | Flask routing, Blueprints, YAML, 301 |
| **B** | Backend (Flask) | Зарегистрировать bp; починить /download (checklist_pdf.html, base_url, weasyprint); заголовки скачивания; fallback при отсутствии weasyprint | Flask, Jinja2, WeasyPrint, HTTP headers |
| **C** | Frontend/Template | Привести checklist.html к эталону (структура, заголовки «Чек-лист организатора»); print/PDF шаблон; изображения Check1/Check11 | Jinja2, HTML5, CSS (print), url_for |
| **D** | UX/Контент | Путь пользователя: читает → скачивает → (опционально) форма/лид; CTA в едином стиле | UX, microcopy, формы |
| **E** | QA | Чек-лист проверки: URL, PDF, картинки, нет 500/JS-ошибок; CSP/консоль; мобильный smoke | QA web, CSP, PDF сверка |
| **F** | SEO | Title/Description/H1 «Чек-лист организатора»; canonical; OpenGraph | On-page SEO, canonical, OG |
| **G** | DevOps/Runtime | WeasyPrint + системные зависимости на хостинге; стабильность генерации PDF; опционально кэш PDF | Linux deps, deploy, performance |

---

## Выполнено (текущий коммит)

### Subagent A (Архитектор)
- Роуты разведены: **канонический URL** — `/projects/contest-org-checklist`, `/projects/contest-org-checklist/download`.
- `/wake-industry` и `/wake-industry/download` — **301 редирект** на канонические URL.
- В `app/__init__.py` зарегистрированы `wake_industry_bp` и `contest_org_checklist_bp`.
- В `configs/showcases/contest_org_checklist.yaml`: `cta_url` изменён на `/projects/contest-org-checklist`.
- В sitemap добавлен slug `contest-org-checklist`.

### Subagent B (Backend)
- Создан `app/routes/contest_org_checklist.py`: страница + download с WeasyPrint, `base_url` для PDF, заголовки `Content-Disposition`, `Cache-Control`.
- Создан шаблон `templates/wake_industry/checklist_pdf.html` (standalone HTML для PDF). При отсутствии weasyprint возвращается 500 с сообщением.

### Subagent C (Frontend)
- В `templates/wake_industry/checklist.html`: заголовки и CTA переведены на переменные `page_title`, `page_heading`, `page_subheading`, `download_pdf_url`; по умолчанию — «Чек-лист организатора соревнований».
- PDF-шаблон — минимальная структура (титул + перечень разделов). **Хвост:** полное соответствие эталону (все пункты и описания в PDF) — задача для Subagent C: вынести контент в `checklist_sections.html` и включить в `checklist_pdf.html`.

### Остальные (D–G)
- SEO (F): title/description/H1 заданы через переменные; canonical остаётся в шаблоне.
- QA (E), UX (D), DevOps (G): проверки и доработки — по плану приёмки ниже.

---

## DoD (Definition of Done) — чек-лист для приёмки

- [ ] Страница открывается по `/projects/contest-org-checklist` без 500/404.
- [ ] `/wake-industry` и `/wake-industry/download` отдают 301 на канонические URL.
- [ ] Ссылка с карточки проекта «Чек-лист для организатора» ведёт на `/projects/contest-org-checklist`.
- [ ] Кнопка «Скачать PDF» ведёт на `/projects/contest-org-checklist/download` и инициирует скачивание PDF.
- [ ] PDF генерируется стабильно (при установленном weasyprint); при отсутствии — корректное сообщение об ошибке.
- [ ] Консоль браузера без ошибок; CSP не нарушается.
- [ ] Title/Description/H1 соответствуют «Чек-лист организатора соревнований».

---

## Артефакты для приёмки

1. Ссылка на ветку/PR.
2. Ссылки: HTML — `/projects/contest-org-checklist`, PDF — `/projects/contest-org-checklist/download`.
3. Скрин/видео: страница + скачивание PDF.
4. Файл PDF для сверки с эталоном.
5. Краткий отчёт: кто что делал, какие риски/хвосты остались (см. «Хвост» выше).

---

## Ограничение области изменений

Работа ведётся **только** в рамках проекта «Чек-лист организатора» и связанных маршрутов/шаблонов/конфигов. Остальные разделы сайта не меняются без явной необходимости.
