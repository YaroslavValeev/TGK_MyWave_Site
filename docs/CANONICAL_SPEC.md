# Каноническая спецификация разделов MyWave

## 1. Общий UI-стандарт

Услуги / Товары / Проекты — единый формат:

- Одинаковый размер карточек (min 280px, max 360px)
- Контейнер изображения: aspect-ratio 16/9, object-fit: cover, object-position: center
- Карусель со стрелками
- Раскрытие карточки по клику (accordion)
- Галерея при 2+ изображениях (стрелки prev/next внутри карточки)
- Единый стиль CTA (btn-secondary «Подробнее», btn-primary «Записаться»/«Купить»)

## 2. Маппинг медиа

### Services
| Папка | Карточка |
|-------|----------|
| static/images/Services/Gym/ | Зал |
| static/images/Services/Boat/ | Катер |
| static/images/Services/Camp/ | Camp |
| static/images/Services/CoachTriper/ | Тренер на выезде |
| static/images/Services/Consalting/ | Консалтинг |

### Shop
| Папка/файл | Карточка |
|------------|----------|
| static/images/Shop/Balanceboard/ | Баланс-борд |
| static/images/Shop/Balanceboard_BIG/ | Баланс-борд BIG |
| static/images/Shop/Balanceboard_Style/ | Баланс-борд NewStyle (15 000 ₽) |
| static/images/Shop/poncho/ | Пончо |
| static/images/Shop/Sertificate/ | Сертификат (30 000 ₽) |
| static/images/Shop/WakeSurfPolia/ | WakeSurf Polia |
| static/images_old/hero-wakesurf.webp | Wave Cards |

### Projects
| Папка/файл | Карточка |
|------------|----------|
| static/images/Project/challenge/ | Wake Challenge |
| static/images/Project/Sufari/ | Wake Surf Safari |
| static/images/Project/CheckList_Competion/ | Чек-лист для организатора |
| static/images/Project/SummerCamp/ | MyWave Ruza Camp |
| static/images/Place1Logo.png | Wake Industry |

## 3. Проекты (порядок)

1. Wake Challenge
2. Wake Surf Safari
3. Чек-лист для организатора
4. MyWave Ruza Camp
5. Wake Industry

CTA «Подробнее» → `/projects/<slug>`

## 4. Модалки

### Gym / Boat — бронирование слота
- Дата → Время → Контакты → Подтверждение

### Camp / CoachTriper / Consulting — заявка (без слотов)
- Программа, что входит, условия
- Форма заявки
- Success-сообщение обязательно (data-success на форме)

## 5. Чек-лист приёмки

- [ ] /, /services, /shop, /projects — без 500
- [ ] Карточки едины по размеру и стилю
- [ ] Изображения: 16/9, cover, center — без искажений
- [ ] Галерея при 2+ изображениях
- [ ] «Подробнее» и «Записаться» работают
