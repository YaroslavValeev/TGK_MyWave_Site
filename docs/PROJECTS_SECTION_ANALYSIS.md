# Анализ раздела «Проекты»

**Дата:** 2025-03-19

---

## 1. Файлы, задействованные в разделе

### Backend
| Файл | Роль |
|------|------|
| `app/__init__.py` | Роуты `/projects`, `/projects/<slug>` (project_detail), projects_page; регистрация blueprints |
| `app/services/showcases.py` | Загрузка YAML-конфигов, `get_project_cards()`, `get_projects_graph()`, маршруты для карточек |
| `app/routes/projects_safari.py` | `/projects/wakesurf-safari`, `/projects/wakesurf-safari-2026` |
| `app/routes/projects/wakesurf_challenge.py` | `/projects/wakesurf-challenge-2025`, формы регистрации |
| `app/routes/wake_industry.py` | `/wake-industry`, `/wake-industry/download` — **НЕ зарегистрирован в app** |
| `app/services/images_resolver.py` | Резолвинг изображений карточек |
| `app/services/project_content.py` | Контент Safari (load_safari_bundle) |

### Конфиги (configs/showcases/)
| Файл | Проект |
|------|--------|
| `wake_challenge.yaml` | WakeSurf Challenge |
| `wakesurf_safari.yaml` | WakeSurf Safari |
| `mywave_ruza_camp.yaml` | MyWave Ruza Camp |
| `contest_org_checklist.yaml` | Чек-лист для организатора |
| `wake_indusrty.yaml` | Wake Industry |
| `sochi_camp.yaml` | (если в channels: projects) |

### Шаблоны
| Файл | Роль |
|------|------|
| `templates/projects.html` | Страница «Все проекты», карусель |
| `templates/index.html` | Секция проектов на главной |
| `templates/partials/project_card_wake_challenge.html` | Карточка WakeSurf Challenge |
| `templates/partials/project_card_wakesurf_safari.html` | Карточка WakeSurf Safari |
| `templates/partials/project_card_ruza_camp.html` | Карточка MyWave Ruza Camp |
| `templates/partials/project_card.html` | Универсальная карточка (checklist, wake industry) |
| `templates/projects/wsc2025.html` | Страница WakeSurf Challenge 2025 |
| `templates/projects/safari.html` | Страница WakeSurf Safari |
| `templates/projects/ruza_camp.html` | Страница MyWave Ruza Camp |

### Статика, контент
| Путь | Роль |
|------|------|
| `static/images/Project/` | Изображения проектов (challenge, Sufari, SummerCamp и т.д.) |
| `static/projects/wsc2025/` | Стили и формы WSC2025 |
| `content/projects/wsc2025/` | Markdown, meta, menu для WSC |
| `content/projects/safari2026/` | Контент Safari |

---

## 2. Маршруты и логика кнопок

### Порядок проектов на витрине
`_PROJECT_ORDER` в showcases.py: `wake_challenge` → `wakesurf_safari` → `checklist` → `mywave_ruza_camp` → `wake_indusrty`

### Маппинг URL карточек

| Проект | card.url | Куда ведёт кнопка «Подробнее» | Фактический роут |
|--------|----------|-------------------------------|-------------------|
| **WakeSurf Challenge** | `/projects/wakesurf-challenge-2025` | Полная страница WSC | `wakesurf_challenge_bp` ✅ |
| **WakeSurf Safari** | `/projects/wakesurf-safari` | Страница Safari | `projects_safari_bp` ✅ |
| **Чек-лист организатора** | `/projects/checklist-org` | Редирект → `/projects#checklist-org` | `project_detail` → якорь ✅ |
| **MyWave Ruza Camp** | `/projects/mywave-ruza-camp` | Страница Ruza Camp | `project_detail` рендерит ruza_camp.html ✅ |
| **Wake Industry** | `/projects/wake-indusrty` | Редирект → `/projects#wake-indusrty` | `project_detail` → якорь ✅ |

### Дополнительные роуты

| URL | Обработчик | Статус |
|-----|------------|--------|
| `/projects/wake-challenge` | Редирект 301 → `/projects/wakesurf-challenge-2025` | ✅ |
| `/projects/wakesurf-safari-2026` | Алиас Safari (тот же шаблон) | ✅ |
| `/wake-industry` | `wake_industry_bp` | ❌ **Blueprint не зарегистрирован** |
| `/wake-industry/download` | PDF чеклиста | ❌ **Недоступен** |

### Кнопки на карточках

| Карточка | Кнопки | Логика |
|----------|--------|--------|
| **Wake Challenge** | «Подробнее», «Стать участником» (collapsed); «Стать тренером», «Стать участником», «Стать спонсором» (expanded) | Все → `p.url` + якорь (#register, #partners) |
| **Safari** | «Подробнее» (collapsed); «Перейти на страницу», «Оставить заявку», «Стать участником» (expanded) | Все → `p.url` (`/projects/wakesurf-safari`) |
| **Ruza Camp** | «Подробнее», «Запросить программу и места» (модалка modalRuzaCamp) | Подробнее → страница; btn-book → модалка |
| **Checklist** | «Подробнее» | → `/projects/checklist-org` → редирект на якорь |
| **Wake Industry** | «Подробнее» | → `/projects/wake-indusrty` → редирект на якорь |

---

## 3. Что работает

- Карусель проектов на главной и на `/projects`
- Выбор partial по `p.id` (wake_challenge, mywave_ruza_camp, wakesurf_safari, остальные)
- Ссылки на полноценные страницы: WSC2025, Safari, Ruza Camp
- Редирект `/projects/wake-challenge` → WSC2025
- Якорные редиректы для checklist и wake industry (`/projects#slug`)
- Модалка Ruza Camp (btn-book + data-modal="modalRuzaCamp") — обрабатывается booking.js
- Резолвинг изображений через images_resolver
- JSON-LD schema (showcase_graph) для SEO

---

## 4. Что доработать

### Критично
1. **wake_industry_bp не зарегистрирован** — `/wake-industry` и `/wake-industry/download` не работают. Карточка «Wake Industry» ведёт на `/projects#wake-indusrty`, а не на страницу чеклиста.
2. **Несоответствие контента**: «Чек-лист для организатора» (checklist) и «Wake Industry» — разные showcase, но wake_industry/checklist.html по смыслу близок к «Чек-лист организатора». Нужно уточнить, куда должна вести каждая карточка.

### Рекомендации
3. **project_detail** для `checklist-org` и `wake-indusrty` — редирект на якорь. Если у проекта есть отдельная страница (как `/wake-industry`), карточка должна вести на неё, а не на якорь.
4. **Опечатка** в `wake_indusrty` (id и slug) — в YAML `wake_indusrty`, лучше `wake_industry`.
5. **Sitemap** — `urls.project_slugs` пуст, в sitemap нет `/projects/<slug>`.
6. **Раскрытие карточки** — используется `services-expand.js` (`.js-expandable-card`), убедиться, что проекты его подхватывают.

---

## 5. Чек-лист для ручной проверки

- [ ] Главная: секция «Проекты», кнопка «Все проекты» → `/projects`
- [ ] Wake Challenge: «Подробнее» → `/projects/wakesurf-challenge-2025`
- [ ] Wake Challenge: «Стать участником» → `#register` на странице WSC
- [ ] Safari: «Подробнее» → `/projects/wakesurf-safari`
- [ ] Ruza Camp: «Подробнее» → `/projects/mywave-ruza-camp`
- [ ] Ruza Camp: «Запросить программу и места» → модалка modalRuzaCamp
- [ ] Checklist: «Подробнее» → `/projects#checklist-org` (скролл к карточке)
- [ ] Wake Industry: «Подробнее» → `/projects#wake-indusrty`
- [ ] `/projects/wake-challenge` → редирект на WSC2025
- [ ] `/projects/wakesurf-safari-2026` → страница Safari
- [ ] Раскрытие карточек по клику (кроме кнопок)
- [ ] Карусель изображений (если 2+ фото)
