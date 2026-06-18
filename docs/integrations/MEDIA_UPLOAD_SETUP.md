# MEDIA Upload Setup (Parser → Site)

Парсер загружает обложку на сайт и получает **публичный** `public_url` для записи в `cover_image_url` / `media_json`.

## Канонические маршруты (оба равнозначны)

Blueprint зарегистрирован с префиксом `/api`, поэтому:

| Метод | Путь | Полный URL |
|--------|------|------------|
| POST | `/media/upload` | **`/api/media/upload`** (канон) |
| POST | `/blog/media/upload` | **`/api/blog/media/upload`** (алиас для старых настроек Parser) |

Auth: `Authorization: Bearer <MEDIA_UPLOAD_TOKEN>` или `X-Media-Upload-Token`  
Формат: `multipart/form-data`, поле `file`  
Успех: **HTTP 201**, в JSON поле `public_url`

Пример ответа (все URL-поля дублируют одно и то же значение для совместимости с Parser):

```json
{
  "ok": true,
  "public_url": "https://mywavetraining.ru/static/uploads/review_media/review_20260423_123000_ab12cd34ef56.jpg",
  "url": "https://mywavetraining.ru/static/uploads/review_media/review_20260423_123000_ab12cd34ef56.jpg",
  "cover_image_url": "https://mywavetraining.ru/static/uploads/review_media/review_20260423_123000_ab12cd34ef56.jpg",
  "image_url": "https://mywavetraining.ru/static/uploads/review_media/review_20260423_123000_ab12cd34ef56.jpg",
  "filename": "review_20260423_123000_ab12cd34ef56.jpg",
  "bytes": 245123
}
```

---

## 1) Переменные окружения сайта (`.env`)

```env
SITE_BASE_URL=https://mywavetraining.ru
MEDIA_UPLOAD_TOKEN=вставь_сюда_результат_secrets_token_urlsafe_без_скобок_и_без_слов_плейсхолдер
MEDIA_UPLOAD_SUBDIR=uploads/review_media
MEDIA_UPLOAD_MAX_BYTES=10485760
```

**Важно:** в значении `MEDIA_UPLOAD_TOKEN` не должно быть подсказок вроде `ТВОЙ_НОВЫЙ_СЕКРЕТ` или `CHANGE_ME` — только реальная длинная строка.  
Одно и то же значение должно быть в **`.env` сайта** и в **конфиге Parser**.

Генерация токена:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Опционально: `MEDIA_UPLOAD_ROOT=...` (абсолютный путь) — только для локальных/тестовых окружений.

### Каталог на сервере (prod / staging)

Директория **не в Git** (см. `.gitignore` → `uploads/`). После деплоя или при **500/507** на upload:

```bash
sudo bash /var/www/mywave/scripts/ensure_media_upload_dirs.sh
sudo systemctl restart mywave-site
```

Диагностика (read-only): `sudo bash automation/production/prod_media_upload_diagnose.sh`

---

## 2) `SITE_BASE_URL` и `http://127.0.0.1:5000`

`SITE_BASE_URL=http://127.0.0.1:5000` допустим **только если** Parser шлёт запрос upload **с той же машины**, где крутится сайт, в тот же порт.  
Если Parser в **другом** процессе на другом хосте, в **Docker/WSL/VM** — `127.0.0.1` указывает *на сеть контейнера/хоста Parser*, а не на Flask. Тогда нужен реальный IP/домен dev-сервера или туннель (ngrok и т.п.) и `SITE_BASE_URL` на этот публичный base URL (или пусто — тогда `public_url` соберётся из `request.host` при upload-запросе).

---

## 3) После правки `.env`

Переменные читаются при старте процесса. Нужен **полный перезапуск** Flask и **перезапуск Parser/бота**, и только потом тест.

---

## 4) Проверка (пошагово)

### Шаг A — API блога (контроль)

```text
GET http://127.0.0.1:5000/api/blog/posts?limit=3
GET http://127.0.0.1:5000/api/blog/latest
```

(На проде замени хост на боевой домен.)

### Шаг B — upload (живой endpoint)

**PowerShell:**

```powershell
curl.exe -X POST "http://127.0.0.1:5000/api/media/upload" `
  -H "Authorization: Bearer <ВСТАВЬ_РЕАЛЬНЫЙ_ТОКЕН_ИЗ_.env>" `
  -F "file=@C:\path\to\test.jpg"
```

Проверь: код **201**, в теле JSON есть **`public_url`**.  
Тот же запрос с тем же токеном должен сработать на алиасе:  
`http://127.0.0.1:5000/api/blog/media/upload`

Если **503** `media upload is not configured` — в процессе сайта **нет** `MEDIA_UPLOAD_TOKEN` (или пустой).  
Если **401** — токен в заголовке не совпадает с `.env`.

### Шаг C — валидация обложки в данных

1. В Sheet / `raw_feed`: поле `cover_image_url` = тот же URL, что вернул upload (начинается с `https://` или `/static/...`).  
2. Открой `public_url` в новой вкладке — должна открыться **картинка** (HTTP 200, не HTML-страница).  
3. Сбрось кэш витрины при необходимости (перезапуск + TTL) и проверь `/blog` и главную.

---

## 5) Что должен делать Parser

1. `POST` файл на `/api/media/upload` **или** `/api/blog/media/upload` с токеном.  
2. Взять `public_url` из JSON.  
3. Записать в `cover_image_url` (и при необходимости в `media_json` / `raw_media`).

Нельзя класть в `cover_image_url` локальные пути, `file_id` и ссылки вида `https://t.me/<channel>/<post_id>` как «картинку».
