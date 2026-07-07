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

**Target:** `main` @ PR #78 merge commit `5d0a1e3d8fd47d2a756e4d72caa8e39426ec757e`

```bash
set -euo pipefail
PROD_ROOT=/var/www/mywave
cd "$PROD_ROOT"
PY="$PROD_ROOT/venv/bin/python"
EXPECTED_HEAD="5d0a1e3d8fd47d2a756e4d72caa8e39426ec757e"

# 1. Код: только main (не detached HEAD, не release-doc SHA)
git -c safe.directory="$PROD_ROOT" fetch origin main
git -c safe.directory="$PROD_ROOT" checkout main
git -c safe.directory="$PROD_ROOT" pull --ff-only origin main
ACTUAL="$(git -c safe.directory="$PROD_ROOT" rev-parse HEAD)"
test "$ACTUAL" = "$EXPECTED_HEAD"

# 2. Зависимости (если менялись)
source venv/bin/activate
pip install -r requirements.txt

# 3. Проверка листов Google Sheets (dry-run; при 503 — повторить через 30–60 с)
DISABLE_TELEGRAM=1 ENABLE_GOOGLE_SERVICES=1 "$PY" scripts/ensure_online_coaching_sheets.py

# 4. Быстрый smoke маршрутов (без dev-сервера, ~5 сек)
DISABLE_TELEGRAM=1 ENABLE_GOOGLE_SERVICES=0 ONLINE_COACHING_ENABLED=1 \
  "$PY" scripts/smoke_online_coaching_routes.py

# 5. Создать листы + заголовки (если dry-run показал missing)
ONLINE_COACHING_SHEETS_APPLY=1 DISABLE_TELEGRAM=1 ENABLE_GOOGLE_SERVICES=1 \
  "$PY" scripts/ensure_online_coaching_sheets.py

# 6. Тесты (опционально на сервере)
DISABLE_TELEGRAM=1 ENABLE_GOOGLE_SERVICES=0 ONLINE_COACHING_ENABLED=1 \
  "$PY" -m pytest tests/unit/test_online_coaching_*.py -q

# 7. Перезапуск приложения (только mywave-site)
sudo systemctl restart mywave-site
sudo systemctl status mywave-site --no-pager

# 8. Smoke (публичный URL; не curl 127.0.0.1:5000 — gunicorn слушает socket)
curl -sI https://mywavewake.ru/services/online-coaching | head -5
curl -sI https://mywavewake.ru/online-coaching | head -5
curl -s https://mywavewake.ru/health/live
```

**Важно:** всегда использовать `$PROD_ROOT/venv/bin/python`, не системный `python3`.
Не переключаться на detached HEAD (`3654bbb2` и др.) — это старый release-doc commit без Online Coaching.

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

## PR #83 deploy (video-step + Telegram video links)

**Target:** `main` @ merge commit `20983b2f7c69d798293dee89df9172b6b18443ff`

```bash
set -euo pipefail
PROD_ROOT=/var/www/mywave
cd "$PROD_ROOT"
PY="$PROD_ROOT/venv/bin/python"
EXPECTED_HEAD="20983b2f7c69d798293dee89df9172b6b18443ff"
SERVICE_USER="${SERVICE_USER:-www-data}"

git -c safe.directory="$PROD_ROOT" fetch origin main
git -c safe.directory="$PROD_ROOT" checkout main
git -c safe.directory="$PROD_ROOT" pull --ff-only origin main
test "$(git -c safe.directory="$PROD_ROOT" rev-parse HEAD)" = "$EXPECTED_HEAD"

# Runtime dirs (required — иначе PermissionError на logs/app.log → 502)
sudo mkdir -p "$PROD_ROOT/logs" "$PROD_ROOT/instance"
sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$PROD_ROOT/logs" "$PROD_ROOT/instance"
sudo find "$PROD_ROOT/logs" -type d -exec chmod 775 {} \;
sudo find "$PROD_ROOT/logs" -type f -exec chmod 664 {} \; 2>/dev/null || true

# Sheets: required for new Online_Requests columns (PR83)
ONLINE_COACHING_SHEETS_APPLY=1 DISABLE_TELEGRAM=1 ENABLE_GOOGLE_SERVICES=1 \
  "$PY" scripts/ensure_online_coaching_sheets.py

DISABLE_TELEGRAM=1 ENABLE_GOOGLE_SERVICES=0 ONLINE_COACHING_ENABLED=1 \
  "$PY" scripts/smoke_online_coaching_routes.py

DISABLE_TELEGRAM=1 ENABLE_GOOGLE_SERVICES=0 ONLINE_COACHING_ENABLED=1 \
  "$PY" -m pytest tests/unit/test_online_coaching_*.py -q

sudo systemctl restart mywave-site
sleep 12

curl -sf https://mywavewake.ru/health/live
curl -sI https://mywavewake.ru/services/online-coaching | head -5
curl -sf https://mywavewake.ru/services/online-coaching | grep -q 'id="oc-video-form"'
```

**Новые колонки `Online_Requests`:** `review_task`, `training_comment`, `training_date`, `spot_or_location`, `in_review_at`, `paid_at`.

**502 после restart:** сначала `journalctl -u mywave-site -n 80` — если `PermissionError` на `logs/app.log` или `.env`, чинить права (см. `docs/ops/PR56_PRODUCTION_INCIDENT_20260627.md`). PR83-код при этом уже на сервере.

**Не трогать:** `mywave-node`, TGbotAdmin, `mywave-telegram-bot`.

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
