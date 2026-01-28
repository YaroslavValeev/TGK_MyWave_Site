# P1: План интеграции CONTRACT-листа в Google Sheets

**Приоритет:** P1 (не блокирует P0)  
**Статус:** Планирование  
**Дата:** 2026-01-28

---

## Цель

Добавить/использовать CONTRACT-лист в Google Sheets как человекочитаемую спецификацию контракта между сайтом и Parser Bot. Это дополняет headers-based валидацию схемы, делая контракт более прозрачным и документированным.

---

## Текущее состояние (P0)

✅ Сайт корректно диагностирует схему по headers листа `raw_feed`  
✅ Валидация required колонок перед writeback  
✅ Коды ошибок для диагностики (`WP_SCHEMA_MISMATCH` и др.)  
✅ Нет зависимости от Parser Bot артефактов (`utils/sheet_schema.py`)

**Риск:** Минимальный — CONTRACT будет опциональным дополнением к headers-based валидации.

---

## Предлагаемая структура CONTRACT-листа

### Колонки листа CONTRACT

| Колонка | Описание | Пример |
|---------|----------|--------|
| `column_name` | Название колонки в raw_feed | `row_number` |
| `required` | Обязательна ли для writeback | `TRUE` / `FALSE` |
| `owner` | Кто заполняет: `parser_bot`, `site`, `both` | `parser_bot` |
| `data_type` | Тип данных | `integer`, `string`, `datetime`, `boolean` |
| `description` | Описание назначения колонки | `Номер строки в таблице для безопасной обратной записи` |
| `validation_rules` | Правила валидации | `>= 2`, `ISO 8601`, `URL format` |
| `error_codes` | Коды ошибок, связанные с колонкой | `WP_ROW_NUMBER_MISSING`, `WP_ROW_NUMBER_INVALID` |

### Пример строки CONTRACT

```
column_name: row_number
required: TRUE
owner: parser_bot
data_type: integer
description: Номер строки в таблице для безопасной обратной записи результатов публикации
validation_rules: >= 2, integer
error_codes: WP_ROW_NUMBER_MISSING, WP_ROW_NUMBER_INVALID
```

---

## План реализации

### Этап 1: Чтение CONTRACT-листа (опционально)

**Файл:** `app/services/blog/contract.py` (новый)

**Функции:**
- `read_contract_sheet(spreadsheet_id, sheet_name="CONTRACT") -> Optional[List[Dict]]`
- `get_contract_column_info(column_name: str) -> Optional[Dict]`
- `validate_against_contract(headers: List[str], contract: List[Dict]) -> Tuple[bool, List[str]]`

**Логика:**
- Если CONTRACT-лист существует — читаем его
- Если нет — используем headers-based валидацию (как сейчас)
- CONTRACT дополняет, но не заменяет headers-based подход

---

### Этап 2: Интеграция с существующей валидацией

**Файл:** `app/services/blog/publish.py`

**Изменения:**
- В `_validate_writeback_schema()` добавить опциональную проверку против CONTRACT
- Если CONTRACT доступен — использовать его для более детальной диагностики
- Логировать, какие колонки отсутствуют согласно CONTRACT

**Пример:**
```python
def _validate_writeback_schema(headers: List[str], contract: Optional[List[Dict]] = None) -> Tuple[bool, List[str]]:
    # Базовая проверка по headers (как сейчас)
    schema_ok, missing_cols = _validate_required_columns(headers, RAW_FEED_REQUIRED_WRITEBACK_COLUMNS)
    
    # Если CONTRACT доступен — дополнительная проверка
    if contract:
        contract_missing = _validate_against_contract(headers, contract)
        if contract_missing:
            logger.info(f"[blog-publish] CONTRACT: отсутствуют колонки: {contract_missing}")
    
    return schema_ok, missing_cols
```

---

### Этап 3: Документация и примеры

**Файлы:**
- `docs/CONTRACT_SHEET_SPEC.md` — спецификация формата CONTRACT-листа
- Пример CONTRACT-листа в документации

---

## Преимущества

1. **Прозрачность:** Человекочитаемая спецификация контракта в самой таблице
2. **Документация:** Описание назначения каждой колонки и правил валидации
3. **Диагностика:** Более детальные сообщения об ошибках на основе CONTRACT
4. **Безопасность:** Опциональность — если CONTRACT отсутствует, работает headers-based валидация

---

## Риски и митигация

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| CONTRACT устарел | Средняя | CONTRACT опционален, headers-based валидация остаётся приоритетной |
| Формат CONTRACT неоднозначен | Низкая | Чёткая спецификация формата в документации |
| Производительность чтения CONTRACT | Низкая | Кэширование CONTRACT на время сессии |

---

## Критерии готовности (DoD)

- [ ] CONTRACT-лист читается опционально (если существует)
- [ ] Валидация работает как с CONTRACT, так и без него
- [ ] Документация формата CONTRACT создана
- [ ] Пример CONTRACT-листа добавлен в документацию
- [ ] Тесты покрывают оба сценария (с CONTRACT и без)

---

## Следующие шаги

1. **Согласование формата CONTRACT** с командой Parser Bot
2. **Создание примера CONTRACT-листа** в тестовой таблице
3. **Реализация чтения CONTRACT** (этап 1)
4. **Интеграция с валидацией** (этап 2)
5. **Тестирование и документация** (этап 3)

---

**Примечание:** P1 не блокирует P0. Можно реализовать после стабилизации P0 в проде.
