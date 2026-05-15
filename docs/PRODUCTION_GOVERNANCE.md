# MyWaveWake — Production Governance

**Production:** https://mywavewake.ru  
**Модель:** production-governed система с разделением **runtime · UX · content · ops**.

Полный scope фазы: [deployment/STABILIZATION_QA_PHASE.md](deployment/STABILIZATION_QA_PHASE.md).

---

## Production статус

Backend operational, runtime стабилен.

Подтверждено: Flask/Gunicorn, Redis, Google integrations, booking slots, Socket.IO, Node proxy, Nginx, SSL, health endpoints, Google Sheets validation, Telegram notifications.

---

## Канонические baselines

| Слой | Commit | Статус |
|------|--------|--------|
| Runtime Foundation | `3de56f8c` | **FROZEN** |
| Frontend/docs | `48dc9c64` | ACTIVE |
| QA/Ops governance | `0a2a0e1a` | ACTIVE |
| Production state/docs | `94fbc211` | ACTIVE |

**Правило:** Runtime Foundation не меняется без issue + rollback plan + smoke strategy + production justification.

---

## Канонические governance-документы

| Документ | Путь |
|----------|------|
| Главный governance | [STABILIZATION_QA_PHASE.md](deployment/STABILIZATION_QA_PHASE.md) |
| UX/mobile scope | [FRONTEND_POLISH_PHASE.md](deployment/FRONTEND_POLISH_PHASE.md) |
| Mobile QA matrix | [MOBILE_QA_MATRIX.md](qa/MOBILE_QA_MATRIX.md) |
| Blog content | [BLOG_CONTENT_VISIBILITY.md](deployment/BLOG_CONTENT_VISIBILITY.md) |
| Incidents | [PRODUCTION_INCIDENT_POLICY.md](ops/PRODUCTION_INCIDENT_POLICY.md) |
| Release gate | [RELEASE_GATE_CHECKLIST.md](deployment/RELEASE_GATE_CHECKLIST.md) |
| Release types | [RELEASE_TYPES.md](deployment/RELEASE_TYPES.md) |
| Server ops | [TIMEWEB_PRODUCTION_RUNBOOK.md](deployment/TIMEWEB_PRODUCTION_RUNBOOK.md) |
| Rollback | [POST_DEPLOY_ROLLBACK.md](deployment/POST_DEPLOY_ROLLBACK.md) |

Эти документы — **единственный канон** для production operations.

---

## Release taxonomy

**ОДИН DEPLOY = ОДИН RELEASE TYPE.**

| Type | Scope |
|------|-------|
| `runtime` | backend / runtime / infrastructure |
| `frontend` | CSS / templates / static UX |
| `content` | blog / parser / Sheets visibility |
| `ops` | monitoring / security / deploy |

Запрещено: смешанный runtime+UX hotfix без отдельного approval.

---

## Обязательный deploy flow

```
Изменение → release type → RELEASE_GATE_CHECKLIST → production_smoke.sh
         → Mobile QA (если frontend) → deploy → post-deploy smoke → rollback при FAIL
```

Скрипты: `scripts/production_smoke.sh`, `scripts/healthcheck.sh`

---

## Обязательные правила (10)

1. Backend runtime frozen.  
2. Frontend — только incremental.  
3. Every deploy → smoke.  
4. Every UX deploy → Mobile QA.  
5. No secrets in Git.  
6. No runtime experiments.  
7. No architecture rewrites.  
8. No direct production hotfixes without smoke.  
9. Stability > feature velocity.  
10. Every change → rollback path.  

---

## Rollback

| Layer | Action |
|-------|--------|
| Frontend | revert UX commit |
| Runtime | rollback to `3de56f8c` |

Обязателен при: health unhealthy (core), booking failure, restart loops, массовых 5xx, smoke FAIL.

---

## Stabilization phase goal

**Exit:** stable · polished · mobile-ready · hardened · observable · investor/demo ready.

**После exit:** SEO, parser scaling, sponsor platform, AI orchestration, tourism ecosystem, advanced analytics, growth automation.

**До exit:** никаких runtime refactor.
