# Decision Log: R2/P0 — Стабилизация интеграции сайта с Parser Bot через Google Sheets

**Дата:** 2026-01-28  
**Owner:** Сайт (Site MyWave)  
**Статус:** ✅ Принято и реализовано

---

## Контекст решения

Интеграция сайта с Parser Bot через Google Sheets (`raw_feed`, `gid=1039755742`) требовала стабилизации обратной записи (writeback) результатов публикации. Существовали риски:

1. **Небезопасная запись**: использование `index+2` как fallback для `row_number` могло привести к записи в неправильную строку при ручных вставках/удалениях в таблице.
2. **Отсутствие обязательных полей**: `canonical_url` не записывался после публикации.
3. **Отсутствие валидации схемы**: ошибки структуры таблицы обнаруживались только при runtime-падениях.
4. **Неясное разделение ответственности**: не было чёткого ownership полей между сайтом и Parser Bot.

---

## Принятое решение (P0)

### 1. Источник истины для сайта

**Решение:** Сайт опирается **только** на headers листа `raw_feed` в Google Sheets.  
**Не опирается:** на `utils/sheet_schema.py` (это артефакт Parser Bot).

**Обоснование:** Сайт и Parser Bot — независимые сервисы. Сайт должен работать автономно, читая контракт напрямую из таблицы.

**Реализация:**
- Валидация схемы по headers листа перед любым writeback
- Коды ошибок: `WP_SCHEMA_MISMATCH`, `WP_ROW_NUMBER_MISSING`, `WP_ROW_NUMBER_INVALID`, `WP_ROW_NUMBER_AMBIGUOUS`

---

### 2. Row-number safety

**Решение:** 
- Приоритет: брать `row_number` из колонки `raw_feed`
- Валидация: `row_number` — целое число и `>= 2`
- Если `row_number` пуст/невалиден: **НЕ выполнять writeback** на проде, ставить `publish_error` с кодом ошибки
- Fallback `index+2` допускается только в тестовом режиме с явным флагом

**Обоснование:** Ручные вставки/удаления строк не должны приводить к записи в неправильную строку.

**Реализация:**
- `_get_row_number_from_record()` — приоритет чтению из колонки
- `_validate_row_number()` — строгая валидация
- `record_publish_error_by_id()` — запись ошибки по уникальному ID, если `row_number` отсутствует

---

### 3. Обязательная запись canonical_url

**Решение:** После успешной публикации формировать `canonical_url = base_url + /blog/{slug}` и записывать в `raw_feed`.

**Обоснование:** `canonical_url` необходим для SEO и внешних ссылок. Сайт знает свой `base_url` и формирует финальный URL.

**Реализация:**
- `_get_public_blog_base_url()` — получение base_url из конфига или fallback `https://mywavetraining.ru`
- `_make_canonical_url(slug)` — формирование полного URL
- `ack_publish()` — запись `canonical_url` после успешной публикации

**Подтверждено:** `base_url = https://mywavetraining.ru`, путь `/blog/{slug}` постоянный (без локализаций/префиксов).

---

### 4. Валидация обязательных колонок перед записью

**Решение:** Перед любым writeback проверять наличие минимальных колонок в headers:
- `row_number`, `status`, `published_posts`, `published_at`
- `publish_attempts`, `publish_last_try_at`, `publish_error`, `canonical_url`

Если чего-то нет: лог + `publish_error=WP_SCHEMA_MISMATCH` (без падения процесса).

**Обоснование:** Ошибки схемы должны проявляться сразу и диагностироваться однозначно.

**Реализация:**
- `_validate_writeback_schema(headers)` — проверка наличия required колонок
- Вызов перед `ack_publish()`, `record_publish_error()`, `publish_ready_posts()`

---

### 5. Ownership полей

**Решение:** Сайт обновляет только "publish-контур" и **не трогает** `ingest`/`process`/`parse` поля бота.

**Минимальный набор, который сайт пишет:**
- `published_posts`, `published_at`
- `canonical_url`
- `publish_attempts`, `publish_last_try_at`, `publish_error`
- `publish_lock_by`, `publish_lock_until`

**Подтверждено:**
- `slug` генерирует **Parser Bot**
- `canonical_url` формирует и пишет **сайт** после публикации

**Обоснование:** Нет взаимного "перетирания" данных между сайтом и ботом.

---

## Доказательства (интеграционная приёмка)

**PR:** https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/7

**Результаты тестирования на реальной таблице:**

1. **Успешный writeback:** строка 198 (`canonical_url` заполнен)
2. **Safety-кейс:** строка 199 (`row_number` пуст → writeback не выполняется, фиксируется `WP_ROW_NUMBER_MISSING`)

---

## Мониторинг и логирование

**Реализовано:**
- Количество `WP_*` кодов ошибок за сессию
- Топ причин `WP_SCHEMA_MISMATCH` (каких колонок не хватило)
- Доля успешных `ack` (успешные / всего попыток)

**Логирование:** В конце каждого запуска `publish_ready_posts()` выводится сводка по P0-кодам.

---

## Следующие шаги (P1, не блокирует P0)

1. **CONTRACT-лист в Google Sheets:** Добавить/использовать как человекочитаемую спецификацию (колонки, required, ownership, статусы, ошибки).
2. **Review queue workflow:** Добавить правила для `review_queue` / `approved_*` / `final_version`.

---

## Релиз и контрольный прогон

### Мерж в main

**Дата:** 2026-01-28  
**Коммит:** `10dcfef7`  
**Статус:** ✅ Выполнено

**Проверка P0-логики после мержа:**
- ✅ `app/services/blog/publish.py` содержит всю P0-логику
- ✅ `app/services/google.py` содержит robust header detection
- ✅ Все P0-патчи сохранены без изменений

---

### Контрольный прогон на проде

**Дата:** _______________  
**Версия:** _______________  
**Проверяющий:** _______________

#### Тест 1: Успешный writeback с canonical_url

- **Строка в таблице:** _______________
- **Ссылка:** _______________
- **Результат:** ✅ / ❌
- **canonical_url:** _______________
- **Замечания:** _______________

#### Тест 2: Safety-кейс (WP_ROW_NUMBER_MISSING)

- **Строка в таблице:** _______________
- **Ссылка:** _______________
- **Результат:** ✅ / ❌
- **publish_error:** _______________
- **Замечания:** _______________

#### Логи P0-мониторинга

- **P0-коды ошибок:** _______________
- **Доля успешных ack:** _______________%
- **Замечания:** _______________

---

## Ссылки

- **PR с реализацией:** https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/7
- **Аудит соответствия:** `docs/BLOG_SHEETS_COMPLIANCE_AUDIT.md`
- **Инструкции по релизу:** `docs/P0_RELEASE_INSTRUCTIONS.md`
- **Настройка редиректов:** `docs/P0_REDIRECTS_SETUP.md`
- **Контрольный прогон:** `docs/P0_CONTROL_RUN.md`
- **Таблица (raw_feed):** https://docs.google.com/spreadsheets/d/1RJpw2mAMej3a-VC6yKAsKkVQvzGStcjUC7LijNNyn50/edit?pli=1&gid=1039755742#gid=1039755742

---

**Решение зафиксировано:** 2026-01-28  
**Мерж в main:** 2026-01-28 (commit `10dcfef7`)  
**Ответственный:** Site MyWave Development Team
