# Media-контур блога: операционный план и DoD

Техническая настройка upload: [MEDIA_UPLOAD_SETUP.md](MEDIA_UPLOAD_SETUP.md).  
Контракт полей в Sheet: [PARSER_DEVELOPER_MEDIA_LETTER.md](PARSER_DEVELOPER_MEDIA_LETTER.md).

## Уже подтверждено (локально)

- `GET /api/blog/latest` и `GET /api/blog/posts` согласованы по `cover_image_url`, `image_url`, `cover`.
- Upload: `POST /api/media/upload`, алиас `POST /api/blog/media/upload`; токен; ответ **201** с `public_url` и алиасами `url` / `cover_image_url` / `image_url`.
- Цепочка: Parser → upload → `public_url` → `raw_feed.cover_image_url` → API → витрина.

## Этап 1. Ручная UI-проверка Parser (2 сценария)

1. Добавление обложки материалу без cover: review → 🖼 → проверка бота, Sheet, `/api/blog/posts`, витрина.
2. Замена обложки: тот же поток; в Sheet новый URL; витрина обновлена.

После массовых правок в Sheet: перезапуск сайта или ожидание TTL кэша блога.

## Этап 2. Controlled backfill

Строки publishable без `cover_image_url`: (1) backfill где есть медиа, (2) важные вручную, (3) архив лишнего.

## Этап 3. Production env

**Сайт:** `SITE_BASE_URL`, `MEDIA_UPLOAD_TOKEN`, `MEDIA_UPLOAD_SUBDIR`, `MEDIA_UPLOAD_MAX_BYTES`.  
**Parser:** те же `SITE_BASE_URL` и токен; `MEDIA_UPLOAD_ENDPOINT=/api/media/upload` (или алиас).  
Перезапуск обоих процессов после смены env.

## Этап 4. Production smoke (внешняя сеть)

1. Upload → 201, публичный URL на боевом домене.  
2. URL открывается с другого устройства/сети.  
3. Запись в `raw_feed`, совпадение в `/api/blog/posts` / `latest`.  
4. Главная, `/blog`, страница поста; hard refresh.

## Definition of Done

1. Оба ручных UI-сценария Parser пройдены.  
2. Backfill / ручные обложки / архив по старым карточкам.  
3. Минимум один production upload через боевой домен; URL с внешней сети.  
4. Витрина и API показывают реальные обложки без ложных URL.

## Checklist (кратко)

- [ ] Production runtime и HTTPS  
- [ ] Secrets: `SITE_BASE_URL`, `MEDIA_UPLOAD_TOKEN`  
- [ ] Nginx/proxy: лимит body, маршрут на Flask  
- [ ] Внешний smoke upload + картинка в браузере  
- [ ] Согласованность API cover-полей  
- [ ] Разбор оставшихся fallback-карточек  

Токен Parser-команде — только защищённым каналом, не в общей переписке.
