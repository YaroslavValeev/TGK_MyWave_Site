# Файлы Wake Challenge для точечного патч-плана

**Назначение:** передать Ярославу ключевые файлы для выдачи правок «файл → блок → замена» (HERO, смысл, секции, табы, CTA, canonical).

**Когда использовать:** после закрытия чек-листа (PR + QA-пакет + «блокеры = 0»), перед следующим спринтом по Wake Challenge.

---

## Список файлов (пути в репозитории)

| Файл | Назначение |
|------|------------|
| `app/routes/projects/wakesurf_challenge.py` | Роут, загрузка контента (menu, meta, sections), формы регистрации, canonical/URL |
| `templates/projects/wsc2025.html` | Вёрстка: HERO, subnav, документы, секции из index.md, партнёры, табы регистрации |
| `static/projects/wsc2025/styles.css` | Стили страницы: HERO (центр, тень/контраст), subnav, секции; убрать лишние бейджи из HERO по заданию |
| `static/js/wsc-subnav.js` | Подсветка пунктов якорной навигации |
| `static/projects/wsc2025/forms.js` | Формы/табы регистрации (если есть) |
| `content/projects/wsc2025/` | Контент: сейчас только `README.md`; при добавлении — `index.md`, `menu.json`, `meta.json`, `judging_criteria.json` |
| `configs/showcases/wsc_2026.yaml` | Карточка на витрине проектов (slug, cta_url) |
| `app/forms/wsc2025_forms.py` | Формы участника/тренера |
| `app/services/projects/wsc2025_service.py` | Сохранение заявок, уведомления |

---

## Где взять содержимое для патч-плана

Для точечных правок «блок → замена» достаточно передать:

1. **Шаблон:** содержимое `templates/projects/wsc2025.html` (целиком или фрагменты HERO, секции «Документы», «Партнёрам», блок регистрации).
2. **Стили:** содержимое `static/projects/wsc2025/styles.css` (особенно HERO и при необходимости общие секции).
3. **Роут:** фрагменты `app/routes/projects/wakesurf_challenge.py` — формирование `meta` (title, description, canonical URL на mywavetreaning.ru), передача в шаблон.
4. **Конфиг витрины:** `configs/showcases/wsc_2026.yaml` (уже в репозитории).
5. **Контент:** при наличии — `content/projects/wsc2025/index.md`, `menu.json`, `meta.json` (сейчас в репозитории только `content/projects/wsc2025/README.md`; menu/meta могут формироваться в коде или подгружаться из других мест — см. `wakesurf_challenge.py`).

---

## Итог для отправки

- Приложить/вставить **содержимое** файлов: `wsc2025.html`, `static/projects/wsc2025/styles.css`, при необходимости фрагменты роута и контента.
- После этого можно получить правки по блокам: HERO, смысл проекта, секции, табы, CTA, canonical.

См. также: `docs/CONTEST_ORG_CHECKLIST_DELIVERY_AND_NEXT_SPRINT.md`, разделы 2 и 7.
