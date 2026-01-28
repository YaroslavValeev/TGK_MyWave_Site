# P0: Статус выполнения задач

**Дата обновления:** 2026-01-28  
**Версия:** `main` (commit `da723c79` и новее)

---

## ✅ Задача 1: Релиз P0 в main

**Статус:** ✅ **ВЫПОЛНЕНО**

- [x] Мерж PR #7 в main (commit `10dcfef7`)
- [x] P0-логика проверена и сохранена
- [x] Все изменения запушены в `main`

**Коммиты:**
- `10dcfef7` - Merge P0: Safe Sheets writeback, canonical_url, monitoring
- `da723c79` - docs: add redirects setup and control run instructions for P0
- `...` - scripts: add P0 control run and canonical URL check scripts

---

## ⏳ Задача 2: Canonical домен + 301 редиректы

**Статус:** ⏳ **ТРЕБУЕТСЯ ВЫПОЛНЕНИЕ НА ПРОДЕ**

**Инструкции:** `docs/P0_REDIRECTS_SETUP.md`

**Чеклист:**
- [ ] Настроены 301-редиректы всех альтернативных доменов на `mywavetreaning.ru`
- [ ] Проверен `SERVER_NAME` (должен быть `mywavetreaning.ru` или не установлен)
- [ ] Проверены reverse-proxy headers (Host фиксируется на canonical)
- [ ] Проверено через `curl -I`: альтернативные домены → 301 на canonical

**Команды для проверки:**
```bash
# Проверка редиректа
curl -I https://mywavetraining.ru/blog/test
# Ожидается: 301 Location: https://mywavetreaning.ru/blog/test

# Проверка SERVER_NAME
echo $SERVER_NAME
# Ожидается: mywavetreaning.ru или пусто (fallback)
```

**Ответственный:** Infra/Redirects team

---

## ⏳ Задача 3: Деплой на прод

**Статус:** ⏳ **ТРЕБУЕТСЯ ВЫПОЛНЕНИЕ НА ПРОДЕ**

**Инструкции:** `docs/P0_DEPLOY_QUICK.md`

**Чеклист:**
- [ ] Код из `main` развёрнут на проде
- [ ] Sanity-check пройден: `python scripts/p0_check_canonical_url.py`
- [ ] Приложение перезапущено и работает корректно

**Команда для sanity-check:**
```bash
python scripts/p0_check_canonical_url.py
```

**Ожидаемый результат:**
```
[SUCCESS] Все проверки пройдены успешно!
   canonical_url формируется корректно: https://mywavetreaning.ru/blog/{slug}
```

**Ответственный:** Deploy team

---

## ⏳ Задача 4: Контрольный прогон (P0 acceptance)

**Статус:** ⏳ **ТРЕБУЕТСЯ ВЫПОЛНЕНИЕ ПОСЛЕ ДЕПЛОЯ**

**Инструкции:** `docs/P0_CONTROL_RUN.md` или `python scripts/p0_control_run.py`

**Чеклист:**
- [ ] Тест 1: Успешный writeback с `canonical_url`
- [ ] Тест 2: Safety-кейс `WP_ROW_NUMBER_MISSING`
- [ ] Результаты зафиксированы в `docs/DECISION_LOG_R2_P0.md`

**Команда для запуска:**
```bash
python scripts/p0_control_run.py
```

**Ответственный:** QA/Control Run team

---

## 📋 Итоговый статус

| Задача | Статус | Ответственный | Ссылка |
|--------|--------|---------------|--------|
| 1. Релиз P0 в main | ✅ Выполнено | Site Dev | commit `10dcfef7` |
| 2. Редиректы + SERVER_NAME | ⏳ Требуется выполнение | Infra/Redirects | `docs/P0_REDIRECTS_SETUP.md` |
| 3. Деплой на прод | ⏳ Требуется выполнение | Deploy | `docs/P0_DEPLOY_QUICK.md` |
| 4. Контрольный прогон | ⏳ Требуется выполнение | QA/Control Run | `docs/P0_CONTROL_RUN.md` |

---

## 🔗 Ссылки на документацию

- **Инструкции по редиректам:** `docs/P0_REDIRECTS_SETUP.md`
- **Инструкции по деплою:** `docs/P0_DEPLOY_QUICK.md`
- **Контрольный прогон:** `docs/P0_CONTROL_RUN.md`
- **Decision Log:** `docs/DECISION_LOG_R2_P0.md`
- **Скрипт проверки canonical_url:** `scripts/p0_check_canonical_url.py`
- **Скрипт контрольного прогона:** `scripts/p0_control_run.py`

---

**Следующий шаг:** Выполнить задачи 2-4 на проде согласно инструкциям.
