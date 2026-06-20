# Руководство Owner: база знаний чата (KB v2)

Как добавлять и редактировать знания **без написания кода**.

## Где лежат файлы

```
knowledge_base/chat/
  boat/          — катер
  gym/           — зал
  booking/       — запись, оплата, отмена
  brand/         — контакты, о бренде
  _meta/         — стиль, routing, CTA (справочно)
```

Один файл = одна тема. Имя файла латиницей: `what_to_bring.md`, `prices.md`.

## Шаблон файла

Скопируйте любой файл Wave 1 и измените поля.

```markdown
---
id: boat_what_to_bring
title: Что взять на катер
category: boat
priority: high
updated_at: 2026-06-19
cta_type: booking_boat
---

# Заголовок

## Когда использовать

- триггер 1
- триггер 2

## Короткий ответ

2–4 предложения — это текст, который чат покажет первым.

## Подробный ответ

Расширение темы для OpenAI и offline fallback.

## Не говорить

- что нельзя обещать

## CTA

Мягкое предложение записаться (текст, не кнопка в PR51).

## Тестовые вопросы

- Вопрос 1?
- Вопрос 2?
- … (минимум 5)
```

## Metadata

| Поле | Описание |
|------|----------|
| `id` | Уникальный ID (латиница, snake_case) |
| `title` | Человекочитаемое название |
| `category` | Папка: boat, gym, booking, brand, … |
| `priority` | high / normal / low |
| `cta_type` | См. `knowledge_base/chat/_meta/cta_buttons.md` |
| `updated_at` | Дата YYYY-MM-DD |

## Критерий качества «10 из 10»

В каждом файле должны быть все секции:

1. Когда использовать
2. Короткий ответ (2–4 предложения)
3. Подробный ответ
4. Кому подходит / сценарий
5. Что делать дальше
6. Не говорить
7. CTA
8. Тестовые вопросы (минимум 5)
9. **Источники** — откуда взяты факты (Owner / config / site / docs / tests)

### Секция «Источники»

```markdown
## Источники

- Config: `configs/services.yaml` — цена/длительность
- Existing site: `templates/index.html` — контакты
- Existing site KB: `knowledge_base/wakesurfing_tips.txt/...`
- Owner-provided project context: PR51 …
```

Если подтверждённого источника нет — не выдумывать; в ответе писать «уточним у менеджера».

## CTA types

Список в [`knowledge_base/chat/_meta/cta_buttons.md`](../../knowledge_base/chat/_meta/cta_buttons.md).

В PR51 `cta_type` передаётся в API; кнопки modal — отдельная задача.

## Цены (canonical)

Сверяйте с [`configs/services.yaml`](../../configs/services.yaml):

- Катер: **10 000 ₽**, 25 минут
- Зал: **3 500 ₽**, 1,5 часа

## Как проверить после правки

```bash
pytest tests/unit/test_knowledge_base_v2.py tests/integration/test_chat_kb_answers.py -q
```

Добавьте свой вопрос в `tests/integration/test_chat_kb_answers.py`, если это важный FAQ.

## Что не делать

- Не удалять `knowledge_base/wakesurfing_tips.txt/` и `projects/*.txt`
- Не писать секреты, пароли, PII в KB
- Не обещать медицинских/юридических гарантий
- Не менять booking flow через чат без approval команды

## Routing (кратко)

- Явно «катер» → не спрашивать «зал или катер»
- «Что взять?» без локации → уточнение
- «Как записаться?» без услуги → выбор Катер / Зал

Полные правила: `knowledge_base/chat/_meta/routing_rules.md`.
