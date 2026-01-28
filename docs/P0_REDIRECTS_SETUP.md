# P0: Настройка 301-редиректов и проверка SERVER_NAME

**Дата:** 2026-01-28  
**Статус:** Требуется выполнение на проде

---

## Цель

Обеспечить консистентность canonical URL и SEO:
- Все альтернативные домены редиректят на canonical `mywavetreaning.ru`
- `canonical_url` всегда формируется одинаково независимо от домена запроса

---

## 1. Canonical домен

**Canonical домен:** `mywavetreaning.ru`  
**Регистрация до:** 12.02.2027  
**Base URL:** `https://mywavetreaning.ru`  
**Путь блога:** `/blog/{slug}`

**Альтернативные домены для редиректа:**
- `mywavetraining.ru` (с правильным написанием)
- `www.mywavetraining.ru`
- `www.mywavetreaning.ru` (www → non-www для canonical)

---

## 2. Настройка 301-редиректов

### Вариант A: Nginx (рекомендуется)

**Файл конфигурации:** `/etc/nginx/sites-available/mywavetreaning.ru` (или аналогичный)

**Полная конфигурация:**

```nginx
# === Canonical домен (mywavetreaning.ru) ===

# HTTP → HTTPS редирект для canonical
server {
    listen 80;
    listen [::]:80;
    server_name mywavetreaning.ru www.mywavetreaning.ru;
    
    return 301 https://mywavetreaning.ru$request_uri;
}

# HTTPS для canonical (основной сайт)
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name mywavetreaning.ru;
    
    # SSL сертификаты (замените на реальные пути)
    ssl_certificate /etc/letsencrypt/live/mywavetreaning.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mywavetreaning.ru/privkey.pem;
    
    # Основной сайт
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host mywavetreaning.ru;  # Фиксируем canonical домен
    }
}

# www → non-www для canonical
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name www.mywavetreaning.ru;
    
    ssl_certificate /etc/letsencrypt/live/mywavetreaning.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mywavetreaning.ru/privkey.pem;
    
    return 301 https://mywavetreaning.ru$request_uri;
}

# === Альтернативные домены → редирект на canonical ===

# mywavetraining.ru (HTTP)
server {
    listen 80;
    listen [::]:80;
    server_name mywavetraining.ru www.mywavetraining.ru;
    
    return 301 https://mywavetreaning.ru$request_uri;
}

# mywavetraining.ru (HTTPS)
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name mywavetraining.ru www.mywavetraining.ru;
    
    # SSL сертификаты для альтернативного домена (если есть)
    # Или используйте тот же сертификат, если он покрывает оба домена
    ssl_certificate /etc/letsencrypt/live/mywavetraining.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mywavetraining.ru/privkey.pem;
    
    return 301 https://mywavetreaning.ru$request_uri;
}
```

**Применение:**

```bash
# Проверка конфигурации
sudo nginx -t

# Если OK — перезагрузка без простоя
sudo systemctl reload nginx

# Или перезапуск (если reload не работает)
sudo systemctl restart nginx
```

**Проверка редиректов:**

```bash
# Проверка HTTP → HTTPS для canonical
curl -I http://mywavetreaning.ru/blog/test
# Ожидается: 301 Location: https://mywavetreaning.ru/blog/test

# Проверка альтернативного домена → canonical
curl -I https://mywavetraining.ru/blog/test
# Ожидается: 301 Location: https://mywavetreaning.ru/blog/test

# Проверка www → non-www для canonical
curl -I https://www.mywavetreaning.ru/blog/test
# Ожидается: 301 Location: https://mywavetreaning.ru/blog/test
```

---

### Вариант B: Apache (.htaccess)

**Файл:** `.htaccess` в корне проекта

```apache
RewriteEngine On

# Редирект альтернативных доменов на canonical
RewriteCond %{HTTP_HOST} ^(www\.)?mywavetraining\.ru$ [NC]
RewriteRule ^(.*)$ https://mywavetreaning.ru/$1 [R=301,L]

# Редирект www на non-www для canonical
RewriteCond %{HTTP_HOST} ^www\.mywavetreaning\.ru$ [NC]
RewriteRule ^(.*)$ https://mywavetreaning.ru/$1 [R=301,L]

# HTTP → HTTPS для canonical
RewriteCond %{HTTPS} off
RewriteCond %{HTTP_HOST} ^(www\.)?mywavetreaning\.ru$ [NC]
RewriteRule ^(.*)$ https://mywavetreaning.ru/$1 [R=301,L]
```

---

### Вариант C: Flask middleware (fallback, если нет reverse proxy)

**Файл:** `app/__init__.py` (добавить в `create_app()`)

```python
@app.before_request
def redirect_non_canonical():
    """Редирект альтернативных доменов на canonical."""
    canonical_domain = 'mywavetreaning.ru'
    host = request.host.lower()
    
    # Список альтернативных доменов
    alternative_domains = [
        'mywavetraining.ru',
        'www.mywavetraining.ru',
        'www.mywavetreaning.ru'
    ]
    
    if host in alternative_domains:
        url = request.url.replace(request.host, canonical_domain)
        return redirect(url, code=301)
    
    # Редирект www на non-www для canonical
    if host == f'www.{canonical_domain}':
        url = request.url.replace(f'www.{canonical_domain}', canonical_domain)
        return redirect(url, code=301)
```

**Примечание:** Этот вариант менее эффективен, так как требует обработки каждого запроса в Flask. Предпочтительнее использовать Nginx/Apache на уровне reverse proxy.

---

## 3. Проверка SERVER_NAME и reverse-proxy

### Цель

Убедиться, что `canonical_url` всегда формируется как `https://mywavetreaning.ru/blog/{slug}` независимо от того, через какой домен пришёл запрос.

### Проверка 1: Переменная окружения SERVER_NAME

**На сервере:**

```bash
# Проверить текущее значение
echo $SERVER_NAME

# Должно быть: mywavetreaning.ru (или не установлено для использования fallback)
```

**Настройка (если нужно явно задать):**

**Вариант A: В systemd service файле**

```ini
[Service]
Environment="SERVER_NAME=mywavetreaning.ru"
```

**Вариант B: В .env файле**

```bash
SERVER_NAME=mywavetreaning.ru
```

**Вариант C: В ProductionConfig**

```python
# config.py
class ProductionConfig(Config):
    # ...
    SERVER_NAME = 'mywavetreaning.ru'  # Явно задаём canonical домен
```

---

### Проверка 2: Код в publish.py

**Файл:** `app/services/blog/publish.py`

**Функция `_get_public_blog_base_url()`:**

```python
def _get_public_blog_base_url() -> str:
    """
    Базовый URL для canonical_url.
    Если в конфиге задан SERVER_NAME, используем его. Иначе fallback на canonical домен проекта.
    
    Canonical домен: mywavetreaning.ru (регистрация до 12.02.2027)
    Альтернативные домены должны редиректить на canonical.
    """
    try:
        server_name = (current_app.config.get("SERVER_NAME") or "").strip() if current_app else ""
    except Exception:
        server_name = ""
    if server_name:
        return f"https://{server_name}".rstrip("/")
    return "https://mywavetreaning.ru"  # Fallback на canonical
```

**Проверка:** Убедиться, что fallback = `https://mywavetreaning.ru`

---

### Проверка 3: Reverse proxy headers

**Проблема:** Если reverse proxy передаёт неправильный `Host` header, это может повлиять на формирование `canonical_url`.

**Решение в Nginx:**

```nginx
location / {
    proxy_pass http://127.0.0.1:5000;
    proxy_set_header Host mywavetreaning.ru;  # Фиксируем canonical домен
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host mywavetreaning.ru;  # Фиксируем canonical домен
}
```

**Важно:** `Host` header должен быть `mywavetreaning.ru`, даже если запрос пришёл через альтернативный домен (после редиректа).

---

### Проверка 4: Тест формирования canonical_url

**На сервере (Python shell):**

```python
from app import create_app
app = create_app('production')

with app.app_context():
    from app.services.blog.publish import _get_public_blog_base_url, _make_canonical_url
    
    # Проверка base_url
    base = _get_public_blog_base_url()
    print(f"Base URL: {base}")
    # Ожидается: https://mywavetreaning.ru
    
    # Проверка canonical_url
    canonical = _make_canonical_url("test-slug")
    print(f"Canonical URL: {canonical}")
    # Ожидается: https://mywavetreaning.ru/blog/test-slug
    
    # Проверка с разными доменами в запросе (симуляция)
    # Должно быть одинаково независимо от Host header
```

---

## 4. Чеклист проверки

- [ ] Все альтернативные домены редиректят на `mywavetreaning.ru` (301)
- [ ] Проверено через `curl -I`: альтернативные домены → 301 на canonical
- [ ] SSL сертификаты настроены для всех доменов
- [ ] `SERVER_NAME` установлен в `mywavetreaning.ru` или не установлен (используется fallback)
- [ ] `_get_public_blog_base_url()` возвращает `https://mywavetreaning.ru`
- [ ] Reverse proxy фиксирует `Host` header на `mywavetreaning.ru`
- [ ] Тест формирования `canonical_url` показывает правильный домен

---

## 5. Документирование результата

После настройки зафиксировать:

**Дата настройки:** _______________  
**Тип инфраструктуры:** Nginx / Apache / Flask middleware  
**Проверено:** ✅ / ❌  
**Замечания:** _______________

---

**Следующий шаг:** После настройки редиректов выполнить контрольный прогон (пункт 3).
