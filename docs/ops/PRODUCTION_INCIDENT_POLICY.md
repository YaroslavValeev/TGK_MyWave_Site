# Production Incident Policy — MyWaveWake

**Фаза:** Production Stabilization + QA Discipline  
| Baseline | Commit | Статус |
|----------|--------|--------|
| Runtime Foundation | `3de56f8c` | FROZEN |
| Frontend/docs | `48dc9c64` | ACTIVE |
| QA/Ops governance | `0a2a0e1a` | ACTIVE |

**Production:** https://mywavewake.ru · Governance: [STABILIZATION_QA_PHASE.md](../deployment/STABILIZATION_QA_PHASE.md)

---

## Цель

Сохранить стабильность runtime при UX-polish и content/ops работах. Любой инцидент — управляемый откат, smoke, фиксация в runbook.

---

## Severity levels

| Level | Название | Примеры | SLA реакции | Действие |
|-------|----------|---------|-------------|----------|
| **SEV-1** | Полный outage | 502/503 на главной, Gunicorn down, DB недоступна | немедленно | Rollback runtime + smoke + postmortem |
| **SEV-2** | Критический функционал | booking slots 5xx, `/health` unhealthy (core), chat down | < 30 мин | Rollback или hotfix **только** с approval + rollback plan |
| **SEV-3** | Деградация | blog empty (content), optional health degraded, static 404 | < 4 ч | Content/ops слой; **не** runtime refactor |
| **SEV-4** | Косметика / UX | spacing, carousel snap, typo | следующий UX release | Mobile QA matrix, без prod hotfix |

---

## Rollback triggers (обязательный откат)

Немедленный rollback **без** ожидания root-cause analysis, если:

1. `curl -fsS https://mywavewake.ru/health` → не HTTP 200 или `status: unhealthy` по **core** (database)
2. `scripts/production_smoke.sh` → FAIL на home, health, slots
3. Booking: `GET /api/calendar/slots/<today>?service=boat` → не 200
4. Рост 5xx в nginx error log > 10/min после deploy
5. Gunicorn / Redis / Node proxy restart loop
6. Любое несанкционированное изменение frozen runtime без issue

**Команды:** [POST_DEPLOY_ROLLBACK.md](../deployment/POST_DEPLOY_ROLLBACK.md)

| Слой | Known-good commit |
|------|-------------------|
| Runtime | `3de56f8c` |
| Frontend-only | предыдущий UX commit или `48dc9c64` |

---

## Freeze rules

### Runtime Foundation (frozen)

Без отдельного issue + rollback plan + smoke plan + production justification **запрещено**:

- Flask bootstrap, Gunicorn, SQLAlchemy init
- Redis architecture, Socket.IO runtime
- Google init, booking routing, health architecture
- env loading, runtime patches, websocket architecture

При SEV-1/SEV-2 на runtime: **freeze всех** изменений кроме rollback/fix по issue.

### Frontend UX

При SEV-1/SEV-2: freeze UX-deploy до стабилизации smoke.

### Content Pipeline

При проблемах видимости блога: только Sheets/statuses/parser — **не** blog routing ([BLOG_CONTENT_VISIBILITY.md](../deployment/BLOG_CONTENT_VISIBILITY.md)).

---

## Deploy stop conditions

**Не деплоить** в production, если:

- [ ] `production_smoke.sh` не прошёл на staging/pre-prod или last-known-good
- [ ] Mobile QA matrix не заполнена для затронутых секций (UX deploy)
- [ ] Нет подтверждённого rollback commit
- [ ] Активен SEV-1/SEV-2 без mitigation plan
- [ ] Изменения затрагивают frozen runtime без approval
- [ ] Secrets в diff / `.env` в коммите

---

## Smoke escalation

```
Deploy → production_smoke.sh
         ├─ OK  → зафиксировать в release notes
         └─ FAIL → STOP deploy / rollback
                    ├─ home/blog fail     → проверить Gunicorn, nginx
                    ├─ health fail        → см. health body; не «чинить» health без issue
                    ├─ slots fail         → Google SA / Sheets (ops), не booking refactor
                    └─ static fail        → nginx /static/, путь файла
```

Скрипт: `bash scripts/production_smoke.sh`  
Переменные: `MYWAVE_BASE_URL`, `SMOKE_SLOT_DATE`

---

## Telegram alert flow

1. **Триггер:** smoke FAIL, health unhealthy (core), watchdog, disk > 85%, fail2ban ban spike
2. **Канал:** production alerts (бот из `TELEGRAM_*` / monitoring helper)
3. **Сообщение (шаблон):**
   ```
   [SEV-X] MyWaveWake
   env: production
   url: https://mywavewake.ru
   check: <what failed>
   commit: <git rev>
   action: rollback | investigate | content
   ```
4. **Эскалация:** SEV-1 → немедленный rollback + уведомление; SEV-2 → owner + rollback готовность; SEV-3/4 → ticket, без ночного hotfix

Реализация: `app.services.monitoring.send_monitoring_alert` — см. [monitoring.md](../monitoring.md).

---

## Post-incident

| Шаг | Артефакт |
|-----|----------|
| Timeline | issue / Telegram thread |
| Root cause | слой: Runtime / UX / Content / Ops |
| Fix commit | отдельный, с smoke |
| Prevention | runbook update, QA matrix row |

---

## Связанные документы

| Документ | Назначение |
|----------|------------|
| [RELEASE_GATE_CHECKLIST.md](../deployment/RELEASE_GATE_CHECKLIST.md) | до deploy |
| [MOBILE_QA_MATRIX.md](../qa/MOBILE_QA_MATRIX.md) | после UX deploy |
| [TIMEWEB_PRODUCTION_RUNBOOK.md](../deployment/TIMEWEB_PRODUCTION_RUNBOOK.md) | серверные процедуры |
| [POST_DEPLOY_ROLLBACK.md](../deployment/POST_DEPLOY_ROLLBACK.md) | откат |
