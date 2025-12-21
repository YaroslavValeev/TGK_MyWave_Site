# Быстрая настройка Google Sheets для Safari 2026

## Что нужно сделать

### 1. Получить ID таблицы SafariSite

1. Откройте вашу таблицу **SafariSite** в Google Sheets
2. Скопируйте ID из URL:
   ```
   https://docs.google.com/spreadsheets/d/ВАШ_ID_ТАБЛИЦЫ/edit
   ```
   Пример: `1kyNQVjeLLe4Ra6oWuf84fHqSjUlWXI8MakVMOrCgic0`

### 2. Добавить в .env файл

Откройте `.env` и добавьте (или обновите):
```env
SAFARI_SPREADSHEET_ID=ваш_id_таблицы_здесь
```

**Пример:**
```env
SAFARI_SPREADSHEET_ID=1kyNQVjeLLe4Ra6oWuf84fHqSjUlWXI8MakVMOrCgic0
```

### 3. Создать Service Account (если ещё нет)

Если у вас уже есть файл `config/service_account.json` — пропустите этот шаг.

Если нет — следуйте инструкции в файле `SETUP_GOOGLE_SHEETS.md` (раздел "Шаг 1").

### 4. Предоставить доступ Service Account к таблице

1. Откройте таблицу **SafariSite**
2. Нажмите **Поделиться** (Share)
3. Добавьте email Service Account (находится в `config/service_account.json`, поле `client_email`)
4. Установите права: **Редактор** (Editor)
5. Нажмите **Отправить**

### 5. Создать листы в таблице

Создайте 4 листа с точными названиями:
- `Safari_Leads`
- `Safari_Partners`
- `Safari_Media`
- `Safari_Feedback`

Структуру колонок смотрите в `GOOGLE_SHEETS_SETUP.md`

---

## Проверка

1. Запустите приложение
2. Откройте `/projects/wakesurf-safari`
3. Заполните форму участника
4. Проверьте, что данные появились в листе `Safari_Leads`

---

## Если что-то не работает

Смотрите подробную инструкцию: `SETUP_GOOGLE_SHEETS.md`

