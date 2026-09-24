# Письмо команде Parser: медиа для блога MyWave (prod)

Документ можно переслать целиком.  
Связанные каноны: [BLOG_CANONICAL_MAPPING.md](../architecture/BLOG_CANONICAL_MAPPING.md), [MEDIA_UPLOAD_SETUP.md](MEDIA_UPLOAD_SETUP.md), [BLOG_CONTRACT_v1.md](../BLOG_CONTRACT_v1.md).

---

## Письмо (тело)

**Тема:** Обязательная загрузка фото/видео на сайт при публикации в блог — VPS не достучится до t.me

Привет!

### Контекст (проверено на проде 2026-09-23)

1. Сайт `https://mywavewake.ru` читает витрину блога из Google Sheets `raw_feed`.
2. С **VPS сайта** (Timeweb) до `https://t.me/...` **нет сети**:
   ```text
   curl t.me → Connection timed out
   ```
   Поэтому сайт **не может** сам скачать обложку/видео из Telegram и показать их в `<img>` / `<video>`.
3. Endpoint загрузки на сайт **работает** (smoke Owner):
   ```text
   POST https://mywavewake.ru/api/media/upload
   → HTTP 201
   → public_url = https://mywavewake.ru/static/uploads/review_media/review_....jpg
   ```
4. Сейчас в `raw_feed` часто попадает `https://t.me/<channel>/<id>` (страница поста) или локальный путь Parser. Браузер это как картинку не открывает → на `/blog` логотип-заглушка.

В группе Telegram медиа видно — это ожидаемо: туда бот шлёт файл. На сайт нужен **публичный URL файла на домене сайта** (или внешний CDN).

### Нужно ли менять код Parser?

**Да.** Либо доработать publish-flow, либо гарантированно включить уже имеющийся client (`upload_cover_image` / `prepare_item_media_for_raw_feed` / `maybe_autoupload_local_cover_and_sync_sheet`), если он есть в репо, но **не вызывается** при «Owner: опубликовать» / sync в Sheet.

Одной настройки Sheet недостаточно: без upload в `cover_image_url` останется `t.me/...`.

### Обязательный сценарий при публикации материала на сайт

На машине Parser (там, где Telethon/бот **достучится** до Telegram):

1. **Скачать** фото/видео вложения на диск (не только `post_url` / `file_id`).
2. **Загрузить** файл на сайт:
   ```http
   POST https://mywavewake.ru/api/media/upload
   Authorization: Bearer <MEDIA_UPLOAD_TOKEN>
   Content-Type: multipart/form-data
   file=<binary>
   ```
   Алиас: `/api/blog/media/upload` (тот же контракт).
3. Из ответа 201 взять `public_url` (также в JSON: `url`, `cover_image_url`, `image_url`; для видео — ещё `video_url`).
4. **Записать в raw_feed**:
   - фото → `cover_image_url` = `public_url` (и дублировать в `image_url` / `media_json` при необходимости);
   - видео → `video_url` = `public_url` + элемент в `media_json`: `{"type":"video","url":"<public_url>"}`;
   - **не** писать `t.me/...` в `cover_image_url` / `image_url` как «картинку»;
   - **не** писать локальные пути `downloads/...`, `F:\...`, `file_id:...`.
5. После записи:  
   `POST https://mywavewake.ru/api/blog/cache/invalidate`  
   с тем же Bearer-токеном (иначе витрина может ждать TTL ~120 с).

### Конфиг Parser (env)

Сверить с `.env` сайта (токен уже есть на проде, длина 64):

```env
MEDIA_UPLOAD_URL=https://mywavewake.ru/api/media/upload
# или MEDIA_UPLOAD_ENDPOINT + base URL — как у вас принято в config
MEDIA_UPLOAD_TOKEN=<тот же, что на сайте>
MEDIA_UPLOAD_MAX_BYTES=10485760
# для видео (сайт принимает mp4/webm до 50 МБ):
MEDIA_UPLOAD_VIDEO_MAX_BYTES=52428800
```

Важно: upload должен ходить на **публичный** `https://mywavewake.ru`, не на `127.0.0.1` сайта (если Parser на другой машине).

### Когда вызывать

Минимум — в момент, когда материал становится видимым на сайте (статус `READY_TO_PUBLISH` / `PUBLISHED` / ваш Owner «опубликовать»), **до или вместе** с записью витринных полей в Sheet.

Если медиа нет — оставить `cover_image_url` пустым (сайт покажет логотип). Лучше пусто, чем `t.me/...`.

### Критерий приёмки (DoD)

1. После публикации тестового поста с фото в Sheet:  
   `cover_image_url` открывается в браузере **как картинка** (URL вида  
   `https://mywavewake.ru/static/uploads/review_media/review_....jpg`).
2. `GET https://mywavewake.ru/api/blog/posts?limit=5` — у этого slug  
   `image_url` / `cover_image_url` = тот же URL, **не** `Place1Logo`, **не** `t.me/...`.
3. Страница `/blog/<slug>` показывает фото без ручной правки админки.
4. Для ролика: на странице есть `<video>` или iframe (YouTube и т.п.), не только ссылка «в Telegram».
5. В логах Parser при publish: успех upload (`status 201`) или явная ошибка с `item_id` / `row_number` (без секретов и без полного raw_content).

### Чего сайт делать не будет

- Проксировать/скачивать `t.me` с VPS (сети нет).
- Встраивать iframe Telegram как основной показ (у части клиентов тоже timeout).
- Угадывать картинку из `file_id` без upload.

### Контакты по контракту сайта

- Upload: `POST /api/media/upload` → 201 + `public_url`
- Invalidate: `POST /api/blog/cache/invalidate`
- Read model: `GET /api/blog/posts`
- Нормализация на сайте: `app/services/blog/store.py` (`_extract_cover_image`, `_extract_video_urls_from_row`)

Спасибо!

**Команда сайта MyWave**

---

## Кратко Do / Don’t

| Do | Don’t |
|----|--------|
| Скачать файл → upload на сайт → `public_url` в Sheet | Только `https://t.me/channel/123` в `cover_image_url` |
| `video_url` = публичный mp4/webm с сайта или YouTube | Локальный `downloads/...` / Windows-путь |
| Invalidate кэша после записи | Ждать, что сайт «сам подтянет» из Telegram |
| Логировать `item_id` + результат upload | Класть mp4 в `cover_image_url` |
