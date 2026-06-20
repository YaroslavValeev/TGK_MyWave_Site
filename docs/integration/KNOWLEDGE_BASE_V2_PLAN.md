# Knowledge Base v2 — план (PR51)

## Цель

Управляемая редакционная база знаний для чата MyWave: markdown-файлы с metadata, direct-reply для P0 intent-ов, тестируемые Q&A, без fine-tuning и без изменений booking modal.

## Архитектура

```
knowledge_base/chat/**/*.md     →  app/services/kb_chat/
                                      ├── parser.py
                                      ├── loader.py
                                      ├── matcher.py
                                      ├── direct_replies.py
                                      ├── routing.py
                                      └── snippets.py
                                           ↓
                              POST /chat/api (chat.py)
```

### Слои ответа

1. **Direct KB** — what_to_bring, prices, booking (до OpenAI)
2. **Disambiguation** — «что взять?» / «как записаться?» без услуги
3. **OpenAI + snippets** — legacy `.txt` + KB v2 excerpts
4. **Offline fallback** — PR49 при сбое OpenAI

## Совместимость

| Legacy | Статус PR51 |
|--------|-------------|
| `knowledge_base/wakesurfing_tips.txt/` | Без изменений |
| `knowledge_base/projects/*.txt` | Без изменений |
| `GET /api/knowledge/training` | Append KB v2 short answers |
| PR50 boat what_to_bring | Сохранён; MD — primary, hardcoded — fallback |

## Wave 1 (PR51)

11 content files + 4 `_meta/` docs:

- `boat/`: what_to_bring, first_lesson, safety, prices
- `gym/`: what_to_bring, training_format, prices
- `booking/`: how_to_book, payment, cancellation, booking_disambiguation
- `brand/`: contacts

## Wave 2 (план)

- `services/`, `products/`, `projects/`, `social/` — по матрице ТЗ §7
- Frontend CTA buttons (`cta_type` → modal)
- Admin upload UI — out of scope

## Out of scope PR51

- OpenAI fine-tuning, `.env`, deploy
- Booking orchestrator / modal rewrite
- DB migrations, Google Drive sync

## Deploy

**NOT STARTED** — до GM approval.

## Тесты

```bash
pytest tests/unit/test_knowledge_base_v2.py tests/integration/test_chat_kb_answers.py -q
```

## Git

`knowledge_base/chat/**` tracked via `.gitignore` exception.
