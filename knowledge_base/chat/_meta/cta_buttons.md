# CTA types (Knowledge Base v2)

Типы кнопок/действий для чата. В PR51 передаются в API как `cta_type`; frontend modal — отдельный PR.

| cta_type | Действие (будущее) |
|----------|-------------------|
| `booking_boat` | Открыть модалку записи на катер |
| `booking_gym` | Открыть модалку записи в зал |
| `booking_choose` | Выбор: Катер / Зал |
| `camp_apply` | Форма Camp |
| `coach_apply` | Форма «Тренер на выезде» |
| `consulting_apply` | Форма консалтинга |
| `project_challenge` | `/projects/wakesurf-challenge-2025` |
| `project_safari` | `/projects/wakesurf-safari` |
| `project_ruza_apply` | Заявка Ruza Camp |
| `social_apply` | `/social#social-apply` |
| `contacts` | Показать телефон / Telegram |
| `none` | Без кнопки |

## Suggestions (chips)

Для `booking_choose` API может вернуть:

```json
{"suggestions": ["Катер", "Зал"]}
```

Чат уже умеет показывать chips — без открытия modal.
