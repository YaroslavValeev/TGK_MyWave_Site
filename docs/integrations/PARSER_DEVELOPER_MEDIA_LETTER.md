# Письмо разработчику парсера: медиа и обложки для сайта MyWave

Документ можно переслать целиком или вставить тело письма из раздела ниже.  
Канон витрины блога: [BLOG_CANONICAL_MAPPING.md](../architecture/BLOG_CANONICAL_MAPPING.md), контракт publishable: [BLOG_CONTRACT_v1.md](../BLOG_CONTRACT_v1.md).

---

## Письмо (тело письма)

**Тема:** Google Sheets / raw_feed: для сайта нужен прямой URL изображения в `cover_image_url` / `raw_media` / `media_json`

Привет!

Мы с сайта MyWave подтянули нормализацию обложек и фронт, но витрина блога по-прежнему не может показать оригинальные картинки из части материалов, потому что в таблицу (лист `raw_feed` / соответствующие колонки) попадает **не URL файла изображения**, а ссылка на **страницу поста** в Telegram или внутренний путь.

### Почему это критично

Сайт рендерит обложку как обычный `<img src="...">` в браузере пользователя.  
Браузер умеет грузить только:

- публичный `https://...` (или `http://...`) на **файл изображения**;
- либо путь с нашего же домена, например `/static/...`.

Он **не** умеет:

- «открыть» `https://t.me/channel/123` как картинку (это HTML-страница);
- читать `downloads/review_media/...`, `F:\...`, `file_id:...` с машины, где крутится Parser (у пользователя этих путей нет).

### Ожидаемое поведение парсера / записи в Sheet

1. **Поле `cover_image_url` (предпочтительно)**  
   Содержит **один** прямой URL изображения, например:
   - `https://cdn.example.com/.../photo.webp`
   - `https://.../file/.../image.jpg`

2. **Поле `image_url`**  
   Либо дублирует обложку, либо пустое.  
   **Не кладём** сюда `https://t.me/username/123` как «картинку».

3. **`raw_media` / `media_json`**  
   Допустимы JSON-массивы объектов, у image-элементов должны быть реальные ссылки, например:
   ```json
   [
     {
       "type": "image",
       "url": "https://.../full.jpg",
       "thumbnail_url": "https://.../thumb.jpg"
     }
   ]
   ```
   Сайт умеет вытаскивать `url`, `thumbnail_url`, `src`, `file_url`, `secure_url` и др. (см. `store._extract_media_candidate`).

4. **Если прямой URL на публичный CDN получить нельзя**  
   Тогда варианты на стороне инфраструктуры (отдельное согласование):
   - выкладывать файл в **публично доступное** хранилище и писать этот URL в Sheet;
   - либо отдать на сайт отдельный endpoint-прокси (это уже не «просто парсер в Sheet»).

5. **Плохие значения (пожалуйста, не писать в `cover_image_url` / `image_url` как «картинку»)**

   - `https://t.me/<channel>/<post_id>` — страница поста, не asset;
   - `downloads/review_media/...` — локальный путь Parser-машины;
   - `F:\...` — Windows-путь;
   - Telegram `file_id` без публичного URL;
   - внутренние пути без HTTP.

### Как быстро проверить после фикса

1. В Sheet у проблемной строки: `cover_image_url` или `media_json[0].thumbnail_url` — открывается в браузере **напрямую** как картинка (вкладка показывает только изображение, не HTML).
2. На стороне сайта: `GET /api/blog/posts` — в `items[].image_url` (это нормализованная обложка) **не** должно быть `t.me/.../число` в качестве единственного варианта, если есть реальное медиа.

### Контакт

Если нужен точный список полей, которые читает `app/services/blog/store.py` (`_extract_cover_image`, `_IMAGE_FIELD_KEYS`), напиши — пришлём ссылку на ревью или краткую таблицу полей.

Спасибо!

**Команда сайта MyWave**

---

## Приложение: кратко Do / Don’t

| Do | Don’t |
|----|--------|
| `https://host/path/image.jpg` (200, `Content-Type: image/*`) | `https://t.me/c/.../N` как единственный «url картинки» |
| JSON в `raw_media` с `url` / `thumbnail_url` | Только `file_id` без публичного URL |
| Публичный CDN/статик | `downloads/...` без HTTP |
| Пусто, если картинки нет | Любой не-HTTP путь, видимый только Parser-машине |
| `video_url` = публичный mp4 / YouTube | `t.me/...` как единственное «видео» без загрузки файла |

### Видео (обязательно для автопоказа на сайте)

Сайт **не умеет** встроить файл из Telegram, пока он живёт только внутри TG. Канон:

1. Скачать видео на машине Parser.
2. `POST /api/media/upload` с `video/mp4` (лимит по умолчанию 50 МБ, `MEDIA_UPLOAD_VIDEO_MAX_BYTES`).
3. Записать ответ `public_url` / `video_url` в колонки `video_url` и в `media_json` (`type: video`, `url: public_url`).
4. Для обложки по-прежнему нужен **image** URL (кадр или фото) — не класть mp4 в `cover_image_url`.
5. После записи в Sheet: `POST /api/blog/cache/invalidate` с `MEDIA_UPLOAD_TOKEN`, чтобы витрина не ждала TTL ~120 с.

Если файл на сайт не загружен, витрина покажет превью `og:image` публичного t.me-поста и/или кнопку «Смотреть видео» на пост в Telegram — это запасной путь, не полноценный плеер на сайте.

## Связь с кодом сайта

- Нормализация строки Sheets: `app/services/blog/store._normalize_row_from_sheets`, `_extract_cover_image`, `_extract_video_urls_from_row`
- Ленивая обложка t.me: `GET /blog/media/telegram-preview?u=https://t.me/...`
- API списка постов: `GET /api/blog/posts` (поле `image_url` = нормализованная обложка)
- Ручная регенера кэша Sheets: `POST /api/blog/cache/invalidate` (`invalidate_blog_sheets_cache()`)
