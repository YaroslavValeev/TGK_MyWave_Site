# Настройка Google Sheets для Wake Surf Safari 2026

## Шаг 1: Создание Service Account в Google Cloud Console

### 1.1. Создайте проект в Google Cloud Console

1. Перейдите на https://console.cloud.google.com/
2. Создайте новый проект или выберите существующий
3. Запомните название проекта

### 1.2. Включите Google Sheets API

1. В меню выберите **APIs & Services** → **Library**
2. Найдите **Google Sheets API**
3. Нажмите **Enable** (Включить)
4. Также включите **Google Drive API** (нужен для доступа к таблицам)

### 1.3. Создайте Service Account

1. Перейдите в **APIs & Services** → **Credentials**
2. Нажмите **Create Credentials** → **Service Account**
3. Заполните:
   - **Service account name**: `mywave-safari-service` (или любое другое имя)
   - **Service account ID**: будет создан автоматически
   - **Description**: `Service account for Wake Surf Safari 2026 data collection`
4. Нажмите **Create and Continue**
5. В разделе **Grant this service account access to project**:
   - **Role**: выберите **Editor** (или **Owner** для полного доступа)
6. Нажмите **Continue** → **Done**

### 1.4. Создайте ключ (JSON файл)

1. Найдите созданный Service Account в списке
2. Нажмите на него
3. Перейдите на вкладку **Keys**
4. Нажмите **Add Key** → **Create new key**
5. Выберите **JSON**
6. Нажмите **Create**
7. Файл автоматически скачается (например, `mywave-safari-service-xxxxx.json`)

### 1.5. Переименуйте и переместите файл

1. Переименуйте скачанный файл в `service_account.json`
2. Переместите его в папку `config/` вашего проекта:
   ```
   config/service_account.json
   ```

**⚠️ ВАЖНО:** Этот файл содержит секретные ключи! НЕ коммитьте его в Git!

---

## Шаг 2: Настройка доступа к таблице SafariSite

### 2.1. Откройте вашу таблицу

1. Откройте Google Таблицу **SafariSite**
2. Скопируйте **ID таблицы** из URL:
   ```
   https://docs.google.com/spreadsheets/d/ВАШ_ID_ТАБЛИЦЫ/edit
   ```
   ID таблицы — это часть между `/d/` и `/edit`

### 2.2. Предоставьте доступ Service Account

1. В таблице нажмите кнопку **Поделиться** (Share)
2. В поле **Добавить людей и группы** вставьте **email вашего Service Account**
   - Email выглядит так: `mywave-safari-service@ваш-проект.iam.gserviceaccount.com`
   - Найти email можно в Google Cloud Console → **IAM & Admin** → **Service Accounts**
3. Установите права доступа: **Редактор** (Editor)
4. Снимите галочку **Уведомить людей** (чтобы не отправлять email)
5. Нажмите **Отправить**

**Альтернативный способ:**
- Можно скопировать email из JSON файла (поле `client_email`)

---

## Шаг 3: Настройка .env файла

Откройте файл `.env` в корне проекта и добавьте:

```env
# ID таблицы SafariSite (скопируйте из URL таблицы)
SAFARI_SPREADSHEET_ID=ваш_id_таблицы_здесь

# Или используйте SAFARI_TAB (альтернативное название)
# SAFARI_TAB=ваш_id_таблицы_здесь
```

**Пример:**
```env
SAFARI_SPREADSHEET_ID=1kyNQVjeLLe4Ra6oWuf84fHqSjUlWXI8MakVMOrCgic0
```

---

## Шаг 4: Создание листов в таблице

Создайте следующие листы в таблице **SafariSite**:

1. **Safari_Leads** — для участников
2. **Safari_Partners** — для партнёров
3. **Safari_Media** — для медиа-партнёров
4. **Safari_Feedback** — для обратной связи

Подробные инструкции по структуре колонок смотрите в файле `GOOGLE_SHEETS_SETUP.md`

---

## Шаг 5: Проверка работы

### 5.1. Проверьте файл service_account.json

Убедитесь, что файл находится по пути:
```
config/service_account.json
```

Структура файла должна быть такой:
```json
{
  "type": "service_account",
  "project_id": "ваш-проект-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "mywave-safari-service@ваш-проект.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  ...
}
```

### 5.2. Проверьте .env файл

Убедитесь, что в `.env` указан правильный ID таблицы:
```env
SAFARI_SPREADSHEET_ID=ваш_id_таблицы
```

### 5.3. Тестовая отправка формы

1. Запустите приложение
2. Откройте страницу `/projects/wakesurf-safari`
3. Заполните форму участника
4. Отправьте форму
5. Проверьте, что данные появились в листе `Safari_Leads` таблицы **SafariSite**

---

## Решение проблем

### Ошибка: "FileNotFoundError: service_account.json"

**Решение:**
- Убедитесь, что файл `service_account.json` находится в папке `config/`
- Проверьте путь в конфигурации: `config.py` → `GOOGLE_SERVICE_ACCOUNT_FILE`

### Ошибка: "Permission denied" или "Access denied"

**Решение:**
1. Проверьте, что Service Account имеет доступ к таблице:
   - Откройте таблицу → Поделиться
   - Убедитесь, что email Service Account есть в списке с правами **Редактор**
2. Проверьте, что включены API:
   - Google Sheets API
   - Google Drive API

### Ошибка: "Invalid credentials" или "invalid_grant"

**Решение:**
- Проверьте, что JSON файл не повреждён
- Убедитесь, что используете правильный файл (не старый)
- Попробуйте создать новый ключ в Google Cloud Console

### Данные не сохраняются в таблицу

**Решение:**
1. Проверьте логи приложения на наличие ошибок
2. Убедитесь, что ID таблицы правильный в `.env`
3. Проверьте, что названия листов точно совпадают:
   - `Safari_Leads` (с заглавной S и L)
   - `Safari_Partners`
   - `Safari_Media`
   - `Safari_Feedback`

---

## Безопасность

⚠️ **ВАЖНО:**

1. **НЕ коммитьте** файл `config/service_account.json` в Git
2. Убедитесь, что файл добавлен в `.gitignore`:
   ```
   config/service_account.json
   ```
3. **НЕ делитесь** этим файлом публично
4. Если файл попал в публичный репозиторий:
   - Немедленно удалите Service Account в Google Cloud Console
   - Создайте новый Service Account
   - Скачайте новый JSON файл

---

## Дополнительная информация

- [Документация Google Sheets API](https://developers.google.com/sheets/api)
- [Документация Service Accounts](https://cloud.google.com/iam/docs/service-accounts)
- [Настройка доступа к Google Sheets](https://developers.google.com/sheets/api/guides/authorizing)

