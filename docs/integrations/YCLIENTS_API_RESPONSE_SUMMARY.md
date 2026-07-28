# YCLIENTS API — выжимка ответа support (для команды)

Источник: письмо Ярослава + ответ Филиппа Щигарцова / api@yclients.tech (дубль в support).

## Auth

1. ЛК разработчика → partner Bearer: https://clck.ru/3REPzB  
2. User token приложения **или** `POST /auth` с login/password пользователя филиала.  
3. Приложение должно быть подключено к филиалу.  
4. Заголовок: `Authorization: Bearer <partner>, User <user>`  
5. `Accept: application/vnd.yclients.v2+json`

## ID / данные компании

- Получать через `GET company` API (Company ID у нас уже `2043174`).  
- Staff / Service / timezone — из API после подключения токенов.

## Запись

- `record_id` уникален и **сохраняется после переноса**.  
- Отмена через статус «Клиент не пришел» → `attendance: -1`.

## Источник канала

- Нативный source нельзя.  
- `comment` + `custom_fields`.  
- В API также есть `api_id` для внешнего ID (используем).

## Multi-set

- Допустимы: одна длинная запись **или** несколько подряд.  
- Проще: одна увеличенной длительности.

## Слоты

- График сотрудника + перерывы + существующие записи.  
- Сезонные ограничения — через график в ЛК (подтверждено).

## Webhook

- Документация: https://support.yclients.com/67-69-993--webhooks-v-yclients/  
- Retry нет; любой HTTP-ответ = доставлено.

## Лимиты

- Base: `https://api.yclients.com/api/v1/`  
- 200/min или 5/sec на partner token  
- Токены без срока; ротация через YCLIENTS  
- Тестовой среды нет → тестовая компания  
- OpenAPI нет → Postman

Полный канон внедрения: `docs/integrations/YCLIENTS_INTEGRATION_CANON.md`  
Команды сервера: `docs/deploy/YCLIENTS_SERVER_COMMANDS.md`
