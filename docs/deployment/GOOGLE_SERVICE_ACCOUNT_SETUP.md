# Google Service Account — production setup

## Какой файл нужен

JSON-ключ **Service Account** из Google Cloud Console:

1. APIs & Services → Credentials → Create credentials → Service account key → JSON.
2. Это **не** OAuth client secret и **не** пользовательский `credentials.json`.

В JSON должны быть поля `type`, `project_id`, `private_key_id`, `private_key`, `client_email`.

## Куда положить на сервере

```text
/var/www/mywave/instance/service_account.json
```

Права:

```bash
chown www-data:www-data /var/www/mywave/instance/service_account.json
chmod 600 /var/www/mywave/instance/service_account.json
```

## Переменные `.env`

```env
ENABLE_GOOGLE_SERVICES=true
SPREADSHEET_ID=<id_таблицы_бронирования>
GOOGLE_CALENDAR_ID=<calendar_id@group.calendar.google.com>
DRIVE_FOLDER_ID=<id_папки_drive>
GOOGLE_DRIVE_FOLDER_ID=<id_папки_drive>
GOOGLE_SERVICE_ACCOUNT_FILE=/var/www/mywave/instance/service_account.json
GOOGLE_SHEETS_CREDENTIALS=/var/www/mywave/instance/service_account.json
GOOGLE_APPLICATION_CREDENTIALS=/var/www/mywave/instance/service_account.json
```

## Права в Google

| Ресурс | Действие |
|--------|----------|
| Google Sheet (`SPREADSHEET_ID`) | Поделиться с `client_email` из JSON, роль **Editor** |
| Google Calendar (`GOOGLE_CALENDAR_ID`) | Добавить SA email, право **Make changes to events** |
| Google Drive folder | Editor для SA email |

## Листы таблицы (booking)

| Лист | Назначение |
|------|------------|
| `Schedule` | Статическое расписание слотов |
| `Responses` | Записи бронирований (`GOOGLE_SHEET_NAME`) |
| `Feedback_Reviews` | Отзывы на главной (опционально) |
| `raw_feed` | Блог / Parser pipeline |

## Smoke после настройки

```bash
sudo systemctl restart mywave-site
curl -sS "https://mywavewake.ru/health" | python3 -m json.tool
curl -sS -o /dev/null -w "%{http_code}\n" \
  "https://mywavewake.ru/api/calendar/slots/$(date +%F)?service=boat"
```

Ожидаемо для slots: `200` с JSON-массивом (может быть `[]`).

## Безопасность

- Не коммитить JSON в Git.
- Не логировать `private_key` и полный путь к ключу в публичных логах.
- При утечке — отозвать ключ в GCP и выпустить новый.
