# Owner — Tour Telegram program callback live smoke

**Host only:** `msk-1-vm-9j6k` (не Site `4169037-ep26382`)  
**Containers:** `toutism-api-1` · `toutism-postgres-1`  
**Image gate:** `sha256:05b6f1a1b514a656261241e5c54881afa44e8e72bbc8075c163b2adfe570f79f`  
**Goal:** send program menu → click **only first** program → DB fingerprint unchanged · no status change  

**Pref Site:** YC partner text SENT · camp publish CLOSED  

**Smoke 2026-07-29T203454Z:** **CLOSED PASS**  
- sent=true · messageId=73 · programCount=6  
- fingerprint before=after `35|9b080c31…` · DB unchanged  
- callback errors=NONE · api image unchanged · health healthy  
- `AUTOPUBLISH_EXECUTION=HOLD` · AUDIT_DIR=`/opt/mywave/backups/telegram-program-callback-live-smoke-20260729T203454Z`  

---

## 0) Host gate (обязательно)

```bash
hostname
```

```bash
docker inspect -f 'api={{.State.Status}}/{{.State.Health.Status}} img={{.Image}}' toutism-api-1
```

```bash
docker inspect -f 'db={{.State.Health.Status}}' toutism-postgres-1
```

**PASS:** hostname=`msk-1-vm-9j6k` · api `running/healthy` · image = expected sha · db healthy.  
Если hostname другой — **STOP**, это не Tour.

---

## 1) Правила клика (до запуска)

1. Откроется сообщение «Диагностика меню программ».  
2. Нажать **ТОЛЬКО первую** зелёную кнопку программы.  
3. **Не** жать: Черновик / Проверка / Доработать / Одобрена / На паузе.  
4. Вернуться в терминал → **Enter** на запросе скрипта.  

Ранее «Публикация через Telegram недоступна» = autopublish HOLD (ожидаемо). При чистом smoke статус-кнопки **не** трогать.

---

## 2) Запуск smoke

Вставьте **весь** блок smoke из runbook команды Tour (тот, что с `EXPECTED_HOST="msk-1-vm-9j6k"` и `AUDIT_DIR=...telegram-program-callback-live-smoke-...`).

После `sent: true` — клик по п.1 → Enter в терминале.

---

## 3) PASS criteria (хвост)

```text
TELEGRAM_PROGRAM_CALLBACK_LIVE_SMOKE=COMPLETE
PROGRAM_STATUS_CHANGE=NOT_EXECUTED
PROGRAM_DATABASE_UNCHANGED=PASS
CONTAINER_CHANGE=NOT_EXECUTED
AUTOPUBLISH_EXECUTION=HOLD
AUDIT_DIR=/opt/mywave/backups/telegram-program-callback-live-smoke-...
```

Пришлите: `send-program-menu-result.safe.json` (sent/messageId/webhook) · before/after fingerprint · есть ли callback errors · FINAL RESULT.

---

## Не делать

- запускать на Site `4169037`  
- менять статус программы из TG во время smoke  
- docker recreate / image pull без отдельного GO  
- трактовать Site `camp published` как Tour `programs` publish
