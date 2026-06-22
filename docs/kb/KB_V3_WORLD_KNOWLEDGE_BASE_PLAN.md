# KB v3 — World Knowledge Base Plan (MyWave)

**Статус:** planning / evidence  
**Deploy:** NOT NEEDED (этот этап — только документы и схемы)  
**Scope:** не PR54–PR56; отдельный planning PR до Owner approval на runtime-внедрение

---

## 1. Контекст и проблема

Текущая KB v2 (`knowledge_base/chat/`) закрывает операционные FAQ (зал, катер, запись, цены), но **не разделяет интенты** и **не даёт глубины** по методике, трюкам и мировым трендам.

**Пример intent mismatch (Owner QA):**

| Вопрос пользователя | Ожидаемый интент | Фактический ответ (сейчас) |
|---------------------|------------------|----------------------------|
| «Для чего мне занятия в зале?» | польза, цель, прогресс, связь с водой | «Что взять с собой в зал?» |

Причина: триггеры `is_what_to_bring_question()` срабатывают на слово «зал» раньше, чем распознаётся вопрос о **цели/пользе**; нет отдельной карточки `gym_why_train`.

**Цель KB v3:** не FAQ-список, а **качественная многослойная база** по wakesurf/wakeboard и экосистеме MyWave — с мировыми источниками, методикой Owner и безопасным использованием контента.

---

## 2. Три слоя KB v3

```text
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Public KB                                         │
│  Ответы пользователям сайта / чата (коротко, безопасно)   │
│  Owner: editorial + chat runtime                            │
└───────────────────────────┬─────────────────────────────────┘
                            │ derives from
┌───────────────────────────▼─────────────────────────────────┐
│  Layer 2: Methodology KB                                    │
│  Тренерская методика MyWave: прогрессии, drills, ошибки     │
│  Owner: тренеры + Owner                                     │
└───────────────────────────┬─────────────────────────────────┘
                            │ informed by
┌───────────────────────────▼─────────────────────────────────┐
│  Layer 3: Intelligence KB                                   │
│  Источники, тренды, настроения, анализ (internal_only)      │
│  Owner: Parser Bot pipeline + аналитика                     │
└─────────────────────────────────────────────────────────────┘
```

| Слой | Аудитория | Публикация | Чат |
|------|-----------|------------|-----|
| Public KB | Посетитель сайта | `blog_ready` / публичные MD | `use_for_chat: yes` |
| Methodology KB | Тренеры, Owner | `internal_only` / review | snippets по policy |
| Intelligence KB | Внутренняя команда | `internal_only` | не напрямую; только summary |

---

## 3. Структура папок KB v3

```text
knowledge_base/
  chat/                          # Layer 1 — Public KB (runtime v2, расширяется)
    _meta/
      kb_index.md
      routing_rules.md
      intents.yaml               # NEW v3: явная карта интентов
    boat/
    gym/
      why_train.md               # NEW: «для чего зал»
      what_to_bring.md           # существует
      prices.md
      training_format.md
    booking/
    brand/
    products/
    projects/
    tricks/                      # NEW: публичные краткие описания трюков
    philosophy/                  # NEW: ценности, подход MyWave

  methodology/                   # Layer 2 — Methodology KB
    _schema/
      trick_card.schema.yaml
      progression.schema.yaml
    wakesurf/
      tricks/
      progressions/
      gym_drills/
      trampoline_drills/
    wakeboard/
      tricks/
      progressions/
    cross_training/
      gym/
      trampoline/
      balance/

  intelligence/                  # Layer 3 — Intelligence KB
    _schema/
      source_card.schema.yaml
    sources/
      youtube/
      instagram/
      federations/
      competitions/
      interviews/
      rss/
    trends/
      YYYY-MM/
    sentiment/
    parser_ingest/               # зеркало/ссылки на raw_feed, не дубликат SoT

  v2_legacy/                     # опционально: архив старых .txt при миграции
```

**Принцип:** Layer 1 остаётся совместимым с текущим `app/services/kb_chat/` (MD + front matter). Layers 2–3 — YAML/MD с расширенными схемами; в runtime попадают только через адаптер и policy.

---

## 4. Таксономия дисциплин

| `discipline` | Описание | Примеры тем |
|--------------|----------|-------------|
| `wakesurf` | Вейксерф за катером | старт, pump, airs, spins, contest |
| `wakeboard` | Вейкборд (катер/кикер) | edging, tantrum, invert |
| `gym_training` | Зал MyWave | сила, мобильность, связь с водой |
| `trampoline` | Батут / air awareness | вращения, приземления |
| `balance` | Баланс-борд, proprioception | стойка, реакция |
| `contest_prep` | Подготовка к соревнованиям | run order, scoring, mindset |
| `camp` | Лагеря, интенсивы | программа, быт, прогресс |
| `travel` | Путешествия, сафари | логистика, экипировка |
| `events` | Организация мероприятий | формат, судейство, safety |
| `athlete_dev` | Развитие спортсменов | возраст, нагрузка, recovery |
| `philosophy` | Философия MyWave | миссия, ценности, культура |
| `industry` | Мировые тренды | бренды, дисциплины, медиа |

Теги пересекаются: одна карточка может иметь `discipline: [wakesurf, gym_training]`.

---

## 5. Таксономия трюков и уровней

### Уровни (`level`)

| Код | Название | Критерий |
|-----|----------|----------|
| `L0` | Discovery | знакомство со спортом, без воды |
| `L1` | Beginner | уверенный старт, баланс, первая линия |
| `L2` | Intermediate | базовые манёвры, связки |
| `L3` | Advanced | airs, вращения, contest elements |
| `L4` | Pro / Contest | run-building, стабильность под давлением |

### Категории трюков (`trick_family`)

`surface_ride` · `pump` · `ollie` · `spin` · `invert` · `grab` · `combo` · `dock_start` · `switch` · `fakie` · `rail` (wakeboard)

### Связь с тренировками

Каждая trick card обязана ссылаться на:

- `water_drills` — на воде
- `gym_drills` — в зале MyWave
- `trampoline_drills` — батут (если применимо)

---

## 6. Схема source card (Intelligence KB)

Минимальная карточка источника (`intelligence/sources/**/*.yaml`):

```yaml
source_id: yt_2026_001
date_found: 2026-06-20
source_type: youtube          # youtube | instagram | facebook | telegram | rss | federation | competition | interview | blog | parser_ingest
url: https://...
author: "Rider / Channel name"
title: "How to progress pump"
discipline: [wakesurf]
topic: pump_progression
level: L2
language: en
summary: |
  Краткое пересказанное содержание своими словами (3–8 предложений).
key_insights:
  - insight 1
  - insight 2
use_for_blog: review          # yes | no | review
use_for_chat: no              # yes | no | review
use_for_training_methodology: review
copyright_risk: medium        # low | medium | high
mywave_comment: |
  Комментарий Owner/тренера: согласие, нюансы для наших учеников.
tags: [pump, intermediate, cable_optional]
review_status: draft          # draft | approved | rejected
reviewed_by: null
reviewed_at: null
```

**Правило:** `summary` и `key_insights` — только **пересказ и выводы**, не копипаст транскрипта/статьи.

---

## 7. Схема trick / methodology card (Methodology KB)

```yaml
name: Surface 360
discipline: wakesurf
level: L3
prerequisites:
  - уверенный surface ride
  - контроль веса на задней ноге
main_idea: |
  Одно предложение — суть манёвра.
step_by_step:
  - шаг 1
  - шаг 2
common_mistakes:
  - ошибка → почему
corrections:
  - как исправить
water_drills:
  - drill id или описание
gym_drills:
  - drill id
trampoline_drills:
  - drill id
safety:
  - жилет, дистанция, условия
success_criteria:
  - наблюдаемый критерий успеха
video_references:
  - source_id: yt_2026_001
    note: "угол камеры, таймкод"
mywave_notes: |
  Методика Owner: что делаем на площадке MyWave иначе.
sources:
  - yt_2026_001
review_status: draft
```

Public KB (Layer 1) может содержать **укороченную** версию (`short_answer` + ссылка на methodology), без полного step-by-step в чате для L3+.

### 7.1. Схема intent card (Public KB / routing)

Файл: `knowledge_base/chat/_meta/intents.yaml` или `intelligence/_schema/intent_card.schema.yaml`

```yaml
intent_id: gym_why
title: Зачем занятия в зале
discipline: [gym_training]
service_location: gym
priority: high                    # порядок проверки до what_to_bring
triggers:
  - "для чего"
  - "зачем"
  - "польза"
  - "зачем занятия в зале"
negative_triggers:                # если есть — intent НЕ срабатывает
  - "что взять"
  - "полотенце"
kb_card: gym/why_train.md
cta_type: booking_gym
disambiguate_with: [gym_what_to_bring, gym_price, gym_booking]
golden_questions:
  - "Для чего мне занятия в зале?"
  - "Зачем ходить в зал MyWave?"
must_include_concepts: [польза, прогресс, связь с водой]
must_not_include: [полотенце, что взять, одежда]
review_status: draft
```

**Разделение интентов (Owner QA):**

| Вопрос | intent_id | kb_card |
|--------|-----------|---------|
| «Для чего мне зал?» | `gym_why` | `gym/why_train.md` |
| «Что взять в зал?» | `gym_what_to_bring` | `gym/what_to_bring.md` |
| «Как записаться в зал?» | `gym_booking` | `booking/how_to_book.md` |
| «Сколько стоит зал?» | `gym_price` | `gym/prices.md` |

---

## 8. Правила `blog_ready` / `internal_only` / `needs_review`

| Флаг | Значение | Кто решает |
|------|----------|------------|
| `blog_ready: yes` | Можно в блог / публичную статью | Owner + editorial |
| `blog_ready: review` | Нужна правовая/методическая проверка | Owner |
| `blog_ready: no` | Только KB / internal | default для Intelligence |
| `use_for_chat: yes` | Попадает в snippets чата | auto если `review_status: approved` |
| `use_for_chat: review` | Только после approve | default для новых source |
| `internal_only` | Не показывать пользователю | Intelligence layer, сырые заметки |
| `needs_review` | `review_status != approved` | блокирует chat/blog |
| `rejected_for_blog_but_useful_for_analysis` | Блог отклонён, но материал полезен для Intelligence/Methodology | Owner editorial |

**`rejected_for_blog_but_useful_for_analysis`:** материал из Parser Bot или внешнего источника не прошёл модерацию блога (`use_for_blog: no`, `review_status: rejected`), но сохраняется в Intelligence KB с `use_for_training_methodology: review` и ссылкой на `raw_id` / `source_id` для анализа трендов и методики — **без публикации** и без дословного копирования.

**Review workflow (Owner / тренер):**

```text
1. ingest → source card (draft)
2. triage → assign discipline/topic/copyright_risk
3. review → Owner/тренер: approve | reject | needs_rewrite
4. if approved:
     - Public KB snippet (use_for_chat) OR
     - Methodology card OR
     - blog_ready pipeline (отдельно)
5. if rejected_for_blog_but_useful_for_analysis:
     - intelligence/sources/ only
     - summary + key_insights своими словами
     - link to original
6. audit log: reviewed_by, reviewed_at, mywave_comment
```

**Pipeline статусов:**

```text
draft → review → approved → published_to_chat / published_to_blog
                      ↘ rejected
```

**copyright_risk:**

- `high` → never `blog_ready: yes`, only internal summary + link
- `medium` → blog/chat only after Owner rewrite
- `low` → facts, scores, schedules (federations, results)

---

## 9. Использование данных Parser Bot

**Source of Truth для публикаций:** таблица `raw_feed` (Parser News) — см. `.cursor/rules/site-publisher-context.mdc`.

KB v3 **не дублирует** `raw_feed`. Вместо этого:

| Поле raw_feed | Использование в KB v3 |
|---------------|------------------------|
| `raw_title`, `raw_content`, `raw_html` | Intelligence: черновик summary (internal) |
| `summary`, `excerpt`, `content_md` | Public KB после approve |
| `expert_opinion`, `questions` | Methodology notes |
| `use_for_blog` аналог | маппинг на `use_for_blog` в source card |
| `status`, `ingest_status` | не путать с `review_status` KB |

**Поток:**

```text
Parser Bot → raw_feed (SoT)
     ↓ ingest job (read-only)
intelligence/parser_ingest/{raw_id}.yaml  # source card stub
     ↓ Owner/tренер review
methodology/ + chat/  # approved derivatives
     ↓
Chat snippets / Blog publish (отдельные pipelines)
```

Материалы **не для блога**, но полезные для анализа → `rejected_for_blog_but_useful_for_analysis` + `use_for_blog: no`, `use_for_training_methodology: review`.

**Разрешённые типы источников:** YouTube, Instagram, Facebook, Telegram, RSS, сайты федераций, результаты соревнований, интервью райдеров, блоги, материалы Parser Bot (`raw_feed`), материалы не прошедшие модерацию блога (только Intelligence, см. выше).

---

## 10. Авторские права и безопасное использование

1. **Не копировать** дословно: статьи, субтитры, посты, фото.
2. **Разрешено:** факты (даты, места, результаты), собственный пересказ, списки тегов, ссылки на оригинал.
3. **Видео:** в чате — описание + ссылка; не встраивать чужой контент без лицензии.
4. **Изображения:** только свои или с явным правом; cover блога — отдельный pipeline.
5. **Интервью/цитаты:** короткая цитата (≤ 1 предложение) + attribution, остальное — пересказ.
6. Поле `copyright_risk` обязательно на каждой source card.
7. `high` risk → только Intelligence, без chat/blog до rewrite Owner.

---

## 11. Intent routing — как чат выбирает правильный ответ

### 11.1. Карта интентов (минимум для gym)

| Intent ID | Триггеры (примеры) | KB card | Не путать с |
|-----------|-------------------|---------|-------------|
| `gym_why` | зачем зал, для чего зал, польза зала, зачем занятия в зале | `gym/why_train.md` | what_to_bring |
| `gym_what_to_bring` | что взять, что нужно с собой | `gym/what_to_bring.md` | why |
| `gym_price` | сколько стоит, цена, стоимость | `gym/prices.md` | — |
| `gym_booking` | как записаться, как попасть в зал | `booking/how_to_book` + gym CTA | — |
| `gym_format` | формат, индивидуально, группа | `gym/training_format.md` | — |

Аналогично для `boat_*`, `booking_*`, `trick_*`, `contest_*`.

### 11.2. Порядок классификации (v3)

```text
1. Explicit intent markers («зачем», «для чего», «польза») → why intents
2. Explicit what_to_bring markers → bring intents
3. Price / booking markers (существующие)
4. Service location (boat vs gym)
5. Semantic match по embeddings / matcher (fallback)
6. Disambiguation question (если confidence < threshold)
```

### 11.3. Изменения в runtime (будущие PR, не в этом planning)

- `knowledge_base/chat/_meta/intents.yaml` — декларативная карта
- `app/services/kb_chat/routing.py` — добавить `is_gym_why_question()`, поднять приоритет над `what_to_bring`
- `direct_replies.py` — handler `_try_gym_why` **до** `_try_what_to_bring`
- Тесты: golden questions из Owner QA

**Golden test (обязателен):**

```text
Q: «Для чего мне занятия в зале?»
A: содержит пользу/прогресс/связь с водой
A: НЕ содержит «полотенце», «возьмите», «одежду»
```

---

## 12. План внедрения по PR

| PR | Название | Scope | Deploy |
|----|----------|-------|--------|
| **KB-P0** | Этот документ + schemas в `knowledge_base/methodology/_schema/` | docs only | NOT NEEDED |
| **KB-P1** | `intents.yaml` + `gym/why_train.md` + routing fix | chat runtime | после QA |
| **KB-P2** | Source card ingest stub из raw_feed (read-only) | intelligence/ | staging |
| **KB-P3** | 10–20 approved source cards (ручной Owner) | intelligence/ | NOT NEEDED |
| **KB-P4** | 5 trick cards L1–L2 (methodology) | methodology/ | NOT NEEDED |
| **KB-P5** | Public snippets из methodology (policy gate) | chat | после QA |
| **KB-P6** | Matcher v3: discipline + level filters | chat runtime | после QA |
| **KB-P7** | Owner authoring UI / sheet (опционально) | tooling | TBD |

**Не смешивать с:** PR54 Wake Challenge, PR55 Social, PR56 Social booking — отдельные Owner approvals.

**Rollback:** каждый runtime PR откатывается независимо; KB content — git revert MD/YAML.

---

## 13. Критерии готовности planning этапа

- [x] Три слоя KB описаны
- [x] Структура папок зафиксирована
- [x] Таксономии discipline / level / trick_family
- [x] Схемы source card и trick card
- [x] Правила blog/chat/copyright
- [x] Связь с Parser Bot / raw_feed
- [x] Intent mismatch gym задокументирован + план fix
- [x] PR roadmap без PR54–56

**Следующий шаг после Owner approval:** KB-P1 (intent `gym_why` + golden tests).

---

## 14. Риски

| Риск | Митигация |
|------|-----------|
| Дублирование raw_feed и Intelligence | ingest только stub + ссылка на `raw_id` |
| Copyright violation | `copyright_risk` + review gate |
| Intent regression | golden tests per intent |
| Слишком длинные ответы чата | Public KB = short_answer; methodology отдельно |
| Scope creep в один PR | строгое разделение planning vs runtime PR |

---

*Документ подготовлен: Site Team · Task: KB v3 planning · Deploy: NOT NEEDED*
