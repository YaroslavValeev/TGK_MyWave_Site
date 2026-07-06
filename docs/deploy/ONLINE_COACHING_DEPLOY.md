# MyWave Online Coaching — деплой

## Перед деплоем (Owner)

1. Создать/проверить листы в Admin Google Sheet (`SPREADSHEET_ID`).
2. Добавить env-переменные на сервере.
3. Задеплоить код и перезапустить `mywave-site`.

## Env (.env на сервере)

```env
ONLINE_COACHING_ENABLED=1
ONLINE_COACHING_APPLICATIONS_ENABLED=1
ONLINE_COACHING_ADMIN_ENABLED=1
ONLINE_COACHING_NOTIFICATIONS_ENABLED=1

# уже должны быть:
NOTIFICATION_BOT_TOKEN=...
ADMIN_CHAT_ID=...
SPREADSHEET_ID=...
GOOGLE_SERVICE_ACCOUNT_FILE=...
```

## Команды на сервере (production)

```bash
# 1. Перейти в каталог проекта
cd /var/www/mywave

# 2. Получить код (ветка с Online Coaching)
git fetch origin
git checkout hotfix/booking-confirm-slot-btn-mobile
git pull origin hotfix/booking-confirm-slot-btn-mobile

# 3. Зависимости (если менялись)
source venv/bin/activate
pip install -r requirements.txt

# 4. Проверка листов Google Sheets (dry-run)
python scripts/ensure_online_coaching_sheets.py

# 4b. Быстрый smoke маршрутов (без dev-сервера, ~5 сек)
DISABLE_TELEGRAM=1 ENABLE_GOOGLE_SERVICES=0 ONLINE_COACHING_ENABLED=1 python scripts/smoke_online_coaching_routes.py

# 5. Создать листы + заголовки (если dry-run показал missing)
ONLINE_COACHING_SHEETS_APPLY=1 python scripts/ensure_online_coaching_sheets.py

# 6. Тесты (опционально на сервере)
pytest tests/unit/test_online_coaching_schema.py \
  tests/unit/test_online_coaching_routes.py \
  tests/unit/test_online_coaching_store.py \
  tests/unit/test_online_coaching_payments.py \
  tests/unit/test_online_coaching_notifications.py -q

# 7. Перезапуск приложения
sudo systemctl restart mywave-site
sudo systemctl status mywave-site --no-pager

# 8. Smoke
curl -sI https://mywavewake.ru/services/online-coaching | head -5
curl -s https://mywavewake.ru/health
```

## Smoke после деплоя

1. Открыть https://mywavewake.ru/services/online-coaching
2. Отправить тестовую заявку Video Check
3. Проверить Telegram-уведомление тренеру
4. Проверить строку в `Online_Requests` (Google Sheets)
5. Admin: https://mywavewake.ru/admin/online-coaching (нужен login admin)

## Rollback

```bash
cd /var/www/mywave
git checkout <previous-stable-tag-or-commit>
sudo systemctl restart mywave-site
```

Или без отката кода — выключить фичу:

```env
ONLINE_COACHING_ENABLED=0
```

```bash
sudo systemctl restart mywave-site
```

## Phase 2 (T-Bank API)

Пока оплата полуавтоматическая: ссылка из кабинета Т-Банка → admin UI → «Сохранить ссылку» → «Оплачено».

## Security checklist (Owner)

- [ ] `NOTIFICATION_BOT_TOKEN`, `ADMIN_CHAT_ID`, `SPREADSHEET_ID`, `GOOGLE_SERVICE_ACCOUNT_FILE` — только в `.env`, не в Git
- [ ] Логи не содержат phone/email/goal/injuries целиком (store логирует только id и статусы)
- [ ] Admin UI `/admin/online-coaching` доступен только после `login_required` + `admin_required`
- [ ] Публичный API `/api/online-coaching/apply` — rate limit 5/min, без PII в ответе
- [ ] `ip_hash` в Sheets — salted hash, не raw IP
- [ ] `injuries_or_limits` скрыто в admin list (`sanitize_request_for_admin`)
- [ ] Feature flags OFF по умолчанию — включать осознанно на production
- [ ] После деплоя — smoke без реальных PII клиентов (тестовая заявка)

## Листы Google Sheets (6 вкладок)

| Лист | Назначение |
|------|------------|
| `Online_Requests` | Заявки |
| `Online_Diaries` | Записи дневника |
| `Online_Payments` | Оплаты |
| `Online_Followups` | Follow-up (ручные) |
| `Online_Reviews` | Отзывы (schema only, Phase 2) |
| `Media_Files` | Видео-ссылки |
