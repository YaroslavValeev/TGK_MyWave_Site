# Release Checklist (Sprint 2+)

Обязательный чеклист перед деплоем. Пройдитесь вручную по всем пунктам.

---

## 1. Environment

- [ ] `SECRET_KEY` задан и не пустой
- [ ] `ADMIN_USERNAME` задан (если используется админка)
- [ ] `ADMIN_PASSWORD` задан и достаточно сложный
- [ ] `OPENAI_API_KEY` задан (для чата)
- [ ] `SPREADSHEET_ID` задан (Google Sheets)
- [ ] `GOOGLE_CALENDAR_ID` задан (Google Calendar)
- [ ] `REDIS_URL` задан (если используется)
- [ ] `DATABASE_URL` задан (если используется PostgreSQL)
- [ ] Файл service account (путь из `GOOGLE_SERVICE_ACCOUNT_FILE`) существует

---

## 2. Security

- [ ] Файлы `.env` и `.env.local` не в git (`git status` — не отслеживаются)
- [ ] Секреты не захардкожены в коде
- [ ] `DEBUG=False` в production

---

## 3. Runtime

- [ ] `/health` доступен и возвращает 200
- [ ] `/metrics/health` доступен и возвращает ожидаемый формат
- [ ] Главная страница открывается
- [ ] `/admin/` открывается (если настроена)
- [ ] `/admin/images/` открывается (если настроена)

---

## 4. Booking

- [ ] Чат открывается и отправляет сообщение
- [ ] В Network чат ходит в `/chat/api` (основной endpoint)
- [ ] `/api/chat` работает как compatibility route (не ломается)
- [ ] Первая бронь проходит успешно
- [ ] Повторная идентичная бронь (phone + date + time) отклоняется с сообщением об ошибке

---

## 5. Final Check

- [ ] Smoke-тесты проходят: `pytest tests/smoke/ -v`
- [ ] Integration-тесты проходят: `pytest tests/integration/ -v`
- [ ] Фиксация baseline: зафиксирован commit/tag перед деплоем
  - Commit: _______________
  - Tag (если есть): _______________

---

## Примечания

- Google Sheets — главный источник истины для бронирований. Ошибка Google Calendar не откатывает успешную бронь.
- При partial failure Calendar ошибка логируется с контекстом (date, time, phone, name).
