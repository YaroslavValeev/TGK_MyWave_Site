# P0: Быстрый деплой на прод

**Дата:** _______________  
**Версия:** `main` (commit `10dcfef7` и новее)

---

## Предварительные требования

- [ ] Редиректы настроены (`docs/P0_REDIRECTS_SETUP.md`)
- [ ] `SERVER_NAME` проверен (должен быть `mywavetreaning.ru` или не установлен)
- [ ] Reverse proxy настроен корректно

---

## Шаги деплоя

### 1. Подготовка

```bash
# На сервере
cd /path/to/site
git fetch origin
git checkout main
git pull origin main

# Проверка версии
git log --oneline -1
# Должен быть коммит с P0-патчами (10dcfef7 или новее)
```

### 2. Обновление зависимостей (если нужно)

```bash
# Активировать виртуальное окружение
source venv/bin/activate  # или venv\Scripts\activate на Windows

# Обновить зависимости (если requirements.txt изменился)
pip install -r requirements.txt
```

### 3. Применение миграций БД (если есть)

```bash
flask db upgrade
```

### 4. Sanity-check: Проверка canonical_url

```bash
python scripts/p0_check_canonical_url.py
```

**Ожидаемый результат:**
```
✅ Все проверки пройдены успешно!
   canonical_url формируется корректно: https://mywavetreaning.ru/blog/{slug}
```

Если проверка не прошла — **НЕ ПРОДОЛЖАТЬ** деплой, проверить конфигурацию.

### 5. Перезапуск приложения

**Вариант A: systemd service**

```bash
sudo systemctl restart mywave-site
# или
sudo systemctl restart gunicorn
```

**Вариант B: Supervisor**

```bash
sudo supervisorctl restart mywave-site
```

**Вариант C: Вручную (если используется screen/tmux)**

```bash
# Остановить старый процесс
# Запустить новый
python main.py
# или
gunicorn -w 4 -b 127.0.0.1:5000 main:app
```

### 6. Проверка работоспособности

```bash
# Проверка, что приложение запустилось
curl -I http://localhost:5000/

# Проверка через reverse proxy
curl -I https://mywavetreaning.ru/
```

---

## После деплоя

1. **Выполнить контрольный прогон:** `docs/P0_CONTROL_RUN.md` или `python scripts/p0_control_run.py`
2. **Зафиксировать результаты:** `docs/DECISION_LOG_R2_P0.md`

---

## Откат (если что-то пошло не так)

```bash
# Откат на предыдущий коммит
git log --oneline -5  # Найти предыдущий коммит
git checkout <previous-commit-hash>
sudo systemctl restart mywave-site

# Или откат на предыдущую ветку (если была)
git checkout <previous-branch>
git pull origin <previous-branch>
sudo systemctl restart mywave-site
```

---

**Статус деплоя:** _______________  
**Выполнил:** _______________  
**Замечания:** _______________
