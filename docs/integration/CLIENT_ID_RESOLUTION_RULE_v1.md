# CLIENT_ID_RESOLUTION_RULE_v1

**Версия:** 1.0 (закрыты TBD)  
**Статус:** ✅ утверждено для Phase 1 PR (2026-05-27)  
**Таблица:** `1kyNQVjeLLe4Ra6oWuf84fHqSjUlWXI8MakVMOrCgic0`

---

## 1. Идентификаторы

| ID | Telegram (бот) | Web (Site) |
|----|----------------|------------|
| `telegram_user_id` | primary key в боте | `""` |
| `client_id` | **`str(telegram_user_id)`** | `client_<unix_ts>` или `web_<uuid>`; reuse по phone |
| `phone` | опционально | обязателен |

**Не выдавать** web `client_id` за Telegram ID в summary — для web используется **`WEB_ID: <booking_id>`** (CALENDAR §3.2).

---

## 2. Сценарий A — запись через Telegram (TGbotAdmin)

1. `client_id` = `str(telegram_user_id)`
2. `/start` и поиск клиента — по **`telegram_user_id`**, не по phone
3. Calendar summary: `(ID: {telegram_user_id})`
4. Merge по phone в боте — **нет**

---

## 3. Сценарий B — web-запись (Site Phase 1)

**Алгоритм `client_resolver`:**

```
1. Нормализовать phone → +7XXXXXXXXXX
2. Искать Clients по phone (exact)
3. Если найден:
     - использовать existing.client_id
     - если existing.telegram_user_id задан — НЕ затирать
4. Если не найден:
     - client_id = client_<unix_ts>  (или web_<uuid>)
5. telegram_user_id = ""
6. source = web
```

| Правило | Значение |
|---------|----------|
| Префикс нового id | `client_<unix_ts>` или `web_<uuid>` — **не** numeric Telegram-like |
| Summary marker | `(WEB_ID: <booking_id>)`, не `(ID: client_...)` |

**Idempotency:** см. CALENDAR §8.2 (Site).

---

## 4. Сценарий C — сначала web, потом бот

| Факт TGbotAdmin | Следствие Phase 1 |
|-----------------|-------------------|
| Нет auto-merge по phone | Возможен **второй** `Clients` при первом `/start` в боте |
| Поиск в боте по `telegram_user_id` | web-клиент с пустым tg id не «склеится» сам |

### Future task (вне Phase 1 PR Site)

```text
TGbotAdmin: client merge by phone
```

**Цель:**

- при совпадении phone связать `telegram_user_id` с существующим `client_id`;
- не создавать дубль;
- не перезаписывать данные без проверки.

Site **не** реализует merge на стороне бота в Phase 1.

---

## 5. Anti-overwrite (обязательно)

```python
if existing.get("telegram_user_id") and not incoming.get("telegram_user_id"):
    incoming["telegram_user_id"] = existing["telegram_user_id"]
```

---

## 6. Реализация Site

| Legacy | Phase 1 |
|--------|---------|
| `find_or_create_client()` в `calendar_routes.py` | `app/services/booking/client_resolver.py` |
| `add_or_update_client()` (col0 = telegram) | не использовать для web |

---

## 7. Логирование (без PII)

```text
client_resolved source=web matched_by=phone client_id_tail=Ab12 created=false
client_resolved source=web matched_by=none client_id_tail=Xy99 created=true
booking_duplicate_detected booking_id_tail=c3d4
```

---

## 8. Definition of Done

- [ ] Повторная web-запись → тот же `client_id` при том же phone
- [ ] `telegram_user_id` не затирается
- [ ] Новый web-клиент: `client_*` / `web_*`, не путать с TG id
- [ ] Сценарий C задокументирован как known limitation до TGbotAdmin merge task
