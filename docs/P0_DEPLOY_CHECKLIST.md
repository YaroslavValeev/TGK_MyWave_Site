# P0 Deploy Checklist

**Дата:** _______________  
**Ответственный:** _______________

---

## Pre-deploy

- [ ] PR #7 проверен и одобрен
- [ ] Все тесты пройдены
- [ ] Код проверен на отсутствие регрессий

---

## Deploy Steps

### 1. Мерж в main

- [ ] Переключиться на `main`: `git checkout main`
- [ ] Обновить: `git pull origin main`
- [ ] Смержить: `git merge ci/add-tests-fixes --no-ff`
- [ ] Проверить конфликты (если есть — разрешить)
- [ ] Запушить: `git push origin main`

### 2. Настройка редиректов

- [ ] Определён тип инфраструктуры (Nginx / Apache / Flask middleware)
- [ ] Настроены 301-редиректы для альтернативных доменов
- [ ] Проверено: `curl -I https://mywavetraining.ru/blog/test` → 301 на canonical
- [ ] SSL сертификаты настроены для всех доменов

### 3. Проверка SERVER_NAME

- [ ] Проверена переменная `SERVER_NAME` на проде
- [ ] Проверен fallback в `_get_public_blog_base_url()`
- [ ] Протестировано формирование `canonical_url` в Python shell
- [ ] Reverse proxy не переопределяет Host header

### 4. Деплой на прод

- [ ] Код обновлён на сервере: `git pull origin main`
- [ ] Зависимости установлены: `pip install -r requirements.txt`
- [ ] Миграции выполнены (если есть): `flask db upgrade`
- [ ] Приложение перезапущено без ошибок
- [ ] Основные страницы открываются: `curl -I https://mywavetreaning.ru/blog`

---

## Post-deploy Testing

### Тест 1: Успешный writeback

- [ ] Найдена/создана тестовая запись со статусом `READY_TO_PUBLISH`
- [ ] `row_number` валиден (>= 2)
- [ ] Запущена публикация
- [ ] Проверено в таблице:
  - [ ] `published_posts` = TRUE
  - [ ] `published_at` заполнен
  - [ ] `canonical_url` = `https://mywavetreaning.ru/blog/{slug}`
  - [ ] `publish_error` пуст
- [ ] Ссылка на строку: _______________

### Тест 2: WP_ROW_NUMBER_MISSING

- [ ] Создана тестовая запись без `row_number`
- [ ] Запущена публикация
- [ ] Проверено в таблице:
  - [ ] Writeback НЕ выполнен
  - [ ] `publish_error` = `WP_ROW_NUMBER_MISSING` или `WP_ROW_NUMBER_INVALID`
- [ ] Ссылка на строку: _______________

### Проверка логов

- [ ] Логи показывают P0-мониторинг:
  - [ ] "P0-коды ошибок за сессию"
  - [ ] "Топ отсутствующих колонок"
  - [ ] "Доля успешных ack"

---

## Sign-off

**Релиз выполнен:** ✅ / ❌  
**Дата:** _______________  
**Подпись:** _______________
