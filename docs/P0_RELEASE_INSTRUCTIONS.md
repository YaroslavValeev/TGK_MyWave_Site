# P0 Release Instructions: Мерж PR #7 и деплой на прод

**Дата:** 2026-01-28  
**PR:** https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/7  
**Статус:** Готов к релизу

---

## 1. Мерж PR #7 в main

### Шаги

1. **Проверка текущего состояния:**
   ```bash
   git checkout main
   git pull origin main
   git log --oneline -5  # Проверить последние коммиты
   ```

2. **Мерж ветки `ci/add-tests-fixes`:**
   ```bash
   git merge ci/add-tests-fixes --no-ff -m "Merge P0: Safe Sheets writeback, canonical_url, monitoring"
   ```

3. **Проверка конфликтов:**
   - Если есть конфликты — разрешить вручную, сохранив логику P0
   - Убедиться, что не изменён смысл P0-патчей:
     - `row_number` валидация
     - `canonical_url` запись
     - Schema validation
     - Ownership полей
     - Логирование P0-кодов

4. **Пуш в main:**
   ```bash
   git push origin main
   ```

### DoD (Definition of Done)

- [ ] PR смержен в main без конфликтов
- [ ] Все P0-патчи сохранены без изменений
- [ ] CI зелёный (если есть)
- [ ] Коммит содержит понятное сообщение о P0-изменениях

---

## 2. Настройка 301-редиректов альтернативных доменов

### Цель

Все альтернативные домены (включая `mywavetraining.ru`) должны редиректить на canonical `mywavetreaning.ru` для консистентности SEO и данных в таблице.

### Варианты реализации

#### Вариант A: Nginx (рекомендуется)

**Файл:** `/etc/nginx/sites-available/mywavetreaning.ru` (или аналогичный)

```nginx
# Canonical домен
server {
    listen 80;
    listen [::]:80;
    server_name mywavetreaning.ru www.mywavetreaning.ru;
    
    # Редирект HTTP → HTTPS
    return 301 https://mywavetreaning.ru$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name mywavetreaning.ru www.mywavetreaning.ru;
    
    # SSL сертификаты
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # Основной сайт
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Альтернативные домены → редирект на canonical
server {
    listen 80;
    listen [::]:80;
    server_name mywavetraining.ru www.mywavetraining.ru;
    
    return 301 https://mywavetreaning.ru$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name mywavetraining.ru www.mywavetraining.ru;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    return 301 https://mywavetreaning.ru$request_uri;
}
```

**Проверка:**
```bash
sudo nginx -t  # Проверка конфигурации
sudo systemctl reload nginx  # Перезагрузка без простоя
```

#### Вариант B: Apache (.htaccess)

**Файл:** `.htaccess` в корне проекта

```apache
# Редирект альтернативных доменов на canonical
RewriteEngine On
RewriteCond %{HTTP_HOST} ^(www\.)?mywavetraining\.ru$ [NC]
RewriteRule ^(.*)$ https://mywavetreaning.ru/$1 [R=301,L]

# Редирект www на non-www для canonical
RewriteCond %{HTTP_HOST} ^www\.mywavetreaning\.ru$ [NC]
RewriteRule ^(.*)$ https://mywavetreaning.ru/$1 [R=301,L]
```

#### Вариант C: Flask middleware (если нет reverse proxy)

**Файл:** `app/__init__.py` (добавить перед созданием app)

```python
from flask import request, redirect, url_for

@app.before_request
def redirect_non_canonical():
    """Редирект альтернативных доменов на canonical."""
    canonical_domain = 'mywavetreaning.ru'
    host = request.host.lower()
    
    # Список альтернативных доменов
    alternative_domains = ['mywavetraining.ru', 'www.mywavetraining.ru']
    
    if host in alternative_domains:
        url = request.url.replace(request.host, canonical_domain)
        return redirect(url, code=301)
    
    # Редирект www на non-www для canonical
    if host == f'www.{canonical_domain}':
        url = request.url.replace(f'www.{canonical_domain}', canonical_domain)
        return redirect(url, code=301)
```

### DoD

- [ ] Все альтернативные домены редиректят на `mywavetreaning.ru` (301)
- [ ] Проверено через `curl -I https://mywavetraining.ru/blog/test` → должен быть `301` и `Location: https://mywavetreaning.ru/blog/test`
- [ ] SSL сертификаты настроены для всех доменов

---

## 3. Проверка SERVER_NAME и reverse-proxy

### Цель

Убедиться, что `canonical_url` всегда формируется одинаково независимо от того, через какой домен пришёл запрос.

### Проверка конфигурации

1. **Проверить переменную окружения `SERVER_NAME` на проде:**
   ```bash
   # На сервере
   echo $SERVER_NAME
   # Должно быть: mywavetreaning.ru (или не установлено для использования fallback)
   ```

2. **Проверить код в `app/services/blog/publish.py`:**
   ```python
   # Должно быть:
   def _get_public_blog_base_url() -> str:
       # ...
       return "https://mywavetreaning.ru"  # fallback
   ```

3. **Проверить reverse proxy headers:**
   - Если используется Nginx/Apache, убедиться, что передаётся правильный `Host` header
   - Проверить, что `X-Forwarded-Host` не переопределяет canonical домен

### Настройка SERVER_NAME (опционально)

**Если нужно явно задать SERVER_NAME:**

**Вариант A: Переменная окружения**
```bash
# В .env или systemd service
export SERVER_NAME=mywavetreaning.ru
```

**Вариант B: В ProductionConfig**
```python
# config.py
class ProductionConfig(Config):
    # ...
    SERVER_NAME = 'mywavetreaning.ru'  # Явно задаём canonical домен
```

### Тест формирования canonical_url

```python
# В Python shell на проде
from app import create_app
app = create_app('production')
with app.app_context():
    from app.services.blog.publish import _get_public_blog_base_url, _make_canonical_url
    base = _get_public_blog_base_url()
    print(f"Base URL: {base}")  # Должно быть: https://mywavetreaning.ru
    canonical = _make_canonical_url("test-slug")
    print(f"Canonical URL: {canonical}")  # Должно быть: https://mywavetreaning.ru/blog/test-slug
```

### DoD

- [ ] `SERVER_NAME` установлен в `mywavetreaning.ru` или не установлен (используется fallback)
- [ ] `_get_public_blog_base_url()` всегда возвращает `https://mywavetreaning.ru`
- [ ] `_make_canonical_url()` формирует URL с правильным доменом
- [ ] Reverse proxy не переопределяет Host header на альтернативный домен

---

## 4. Деплой на прод

### Шаги

1. **Подготовка:**
   ```bash
   # На сервере
   cd /path/to/site
   git fetch origin
   git checkout main
   git pull origin main
   ```

2. **Проверка изменений:**
   ```bash
   git log --oneline -5  # Убедиться, что P0-коммиты есть
   git diff HEAD~5 HEAD app/services/blog/publish.py  # Проверить изменения
   ```

3. **Установка зависимостей (если нужно):**
   ```bash
   source venv/bin/activate  # или ваш способ активации venv
   pip install -r requirements.txt
   ```

4. **Миграции БД (если есть):**
   ```bash
   flask db upgrade  # или ваш способ миграций
   ```

5. **Перезапуск приложения:**
   ```bash
   # Systemd
   sudo systemctl restart mywave-site
   
   # Или PM2
   pm2 restart mywave-site
   
   # Или другой способ перезапуска
   ```

6. **Проверка работоспособности:**
   ```bash
   curl -I https://mywavetreaning.ru/blog
   # Должен вернуть 200 OK
   ```

### DoD

- [ ] Код обновлён до версии с P0-патчами
- [ ] Приложение перезапущено без ошибок
- [ ] Основные страницы открываются
- [ ] Логи не показывают критических ошибок

---

## 5. Контрольный прогон после деплоя

### Цель

Проверить, что P0-функциональность работает корректно на проде.

### Тест 1: Успешный writeback

**Шаги:**

1. **Найти или создать тестовую запись в `raw_feed`:**
   - Статус: `READY_TO_PUBLISH`
   - `row_number` заполнен (валидное число >= 2)
   - `published_posts` != TRUE
   - Есть `slug` (или он будет сгенерирован)

2. **Запустить публикацию:**
   ```bash
   # Через cron или вручную
   python -c "from app import create_app; from app.database import db; app = create_app('production'); app.app_context().push(); from app.services.blog.publish import publish_ready_posts; stats = publish_ready_posts(db.session); print(stats)"
   ```

3. **Проверить результат в таблице:**
   - Открыть строку по `row_number` в `raw_feed`
   - Проверить:
     - `published_posts` = TRUE
     - `published_at` заполнен
     - `canonical_url` = `https://mywavetreaning.ru/blog/{slug}`
     - `publish_error` пуст
     - `publish_attempts` увеличен
     - `publish_last_try_at` обновлён

4. **Зафиксировать результат:**
   - Скриншот строки "до" и "после"
   - Ссылка на строку: `https://docs.google.com/spreadsheets/d/1RJpw2mAMej3a-VC6yKAsKkVQvzGStcjUC7LijNNyn50/edit?pli=1&gid=1039755742#gid=1039755742&range=ROW_NUMBER:ROW_NUMBER`

### Тест 2: Safety-кейс (WP_ROW_NUMBER_MISSING)

**Шаги:**

1. **Создать тестовую запись без `row_number`:**
   - Статус: `READY_TO_PUBLISH`
   - `row_number` пуст или невалиден
   - `id` заполнен (для идентификации)

2. **Запустить публикацию** (как в тесте 1)

3. **Проверить результат:**
   - Writeback **НЕ выполнен** (не записаны `published_posts`, `published_at`, `canonical_url`)
   - `publish_error` = `WP_ROW_NUMBER_MISSING` или `WP_ROW_NUMBER_INVALID`
   - `publish_attempts` увеличен
   - `publish_last_try_at` обновлён

4. **Зафиксировать результат:**
   - Скриншот строки с ошибкой
   - Ссылка на строку

### Проверка логов

**Проверить логи приложения на наличие P0-мониторинга:**
```bash
# На сервере
tail -n 100 /var/log/mywave/app.log | grep "blog-publish"
# Должны быть строки:
# - "P0-коды ошибок за сессию"
# - "Топ отсутствующих колонок (WP_SCHEMA_MISMATCH)"
# - "Доля успешных ack"
```

### DoD

- [ ] Тест 1 пройден: успешный writeback с `canonical_url`
- [ ] Тест 2 пройден: writeback не выполнен, установлен `WP_ROW_NUMBER_MISSING`
- [ ] Ссылки на строки в таблице зафиксированы
- [ ] Логи показывают P0-мониторинг
- [ ] Скриншоты/логи сохранены в отчёт

---

## Отчёт о релизе

После выполнения всех шагов заполнить:

**Дата релиза:** _______________  
**Версия:** _______________ (commit hash)  
**Ответственный:** _______________

### Результаты тестов

**Тест 1 (успешный writeback):**
- Строка в таблице: _______________
- Ссылка: _______________
- Результат: ✅ / ❌

**Тест 2 (WP_ROW_NUMBER_MISSING):**
- Строка в таблице: _______________
- Ссылка: _______________
- Результат: ✅ / ❌

### Проблемы и замечания

_______________

---

**Следующие шаги:** После успешного релиза можно переходить к P1 (CONTRACT-лист).
