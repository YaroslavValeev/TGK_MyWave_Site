# Runtime Governance — MyWaveWake

**Production:** https://mywavewake.ru  
**Governance index:** [PRODUCTION_GOVERNANCE.md](../PRODUCTION_GOVERNANCE.md)  
**Operational scope:** [STABILIZATION_QA_PHASE.md](STABILIZATION_QA_PHASE.md)

Runtime Foundation — **production infrastructure foundation**. Formal freeze действует с baseline `3de56f8c`.

---

## Frozen baseline

| Layer | Commit | Status |
|-------|--------|--------|
| **Runtime Foundation** | `3de56f8c` | **FROZEN** |

Runtime рассматривается как неизменяемый слой до explicit approval через governance process.

---

## Change control (обязательно для любого runtime change)

1. Отдельный issue с описанием риска  
2. Rollback plan (target: `3de56f8c`)  
3. Smoke strategy (`production_smoke.sh` + health + slots)  
4. Production justification  

Без всех четырёх пунктов — **change rejected**.

Release type: `runtime` only. См. [RELEASE_TYPES.md](RELEASE_TYPES.md).

---

## Freeze scope

Без explicit approval **не изменяются**:

| Область | Компоненты |
|---------|------------|
| App bootstrap | Flask `create_app`, extensions init |
| Process model | Gunicorn wiring, workers, eventlet |
| Persistence | SQLAlchemy init, `app.database.models.db` |
| Cache / limits | Redis architecture, Flask-Limiter backend |
| Realtime | Socket.IO runtime, websocket architecture |
| Product API | booking API architecture (`calendar_routes`, slots) |
| Integrations | Google services init (Sheets, Calendar, Drive) |
| Config | env loading, secrets resolution |
| Observability | health routing (`app/routes/health.py`) |
| Edge runtime | runtime SSL/DNS patches |

---

## Запрещено

- runtime refactor «заодно» с UX  
- async rewrites  
- migration chaos  
- architecture experiments  
- direct production hotfix без smoke  
- смешанный **runtime + frontend** deploy (см. RELEASE_TYPES)

---

## Rollback policy

| Trigger | Action |
|---------|--------|
| health unhealthy (core / database) | немедленный rollback к `3de56f8c` |
| booking failure (slots 5xx) | rollback + smoke |
| Gunicorn restart loops | rollback |
| массовые 5xx после deploy | rollback |
| `production_smoke.sh` FAIL | rollback или stop deploy |

Процедура: [POST_DEPLOY_ROLLBACK.md](POST_DEPLOY_ROLLBACK.md)  
Инциденты: [PRODUCTION_INCIDENT_POLICY.md](../ops/PRODUCTION_INCIDENT_POLICY.md)

```bash
cd /var/www/mywave
git checkout 3de56f8c
/var/www/mywave/venv/bin/pip install -r requirements.txt  # если менялись deps
sudo systemctl restart mywave-site
bash scripts/production_smoke.sh
```

---

## Smoke (runtime deploy)

Обязательные проверки после любого runtime change:

```bash
MYWAVE_BASE_URL=https://mywavewake.ru bash scripts/production_smoke.sh
curl -sS https://mywavewake.ru/health | head -c 500
```

Gate: [RELEASE_GATE_CHECKLIST.md](RELEASE_GATE_CHECKLIST.md).

---

## Связь с другими слоями

| Слой | Может меняться без runtime approval |
|------|-------------------------------------|
| Frontend UX | CSS, templates, static (baseline `48dc9c64`) |
| Content | Sheets statuses, parser (не blog routing code) |
| Ops | nginx, fail2ban, cron, monitoring scripts |

Изменения в других слоях **не должны** затрагивать freeze scope.

---

## До завершения stabilization phase

**Никаких runtime refactor.**  
Exit criteria: [STABILIZATION_QA_PHASE.md](STABILIZATION_QA_PHASE.md#цель-фазы-exit-criteria).
