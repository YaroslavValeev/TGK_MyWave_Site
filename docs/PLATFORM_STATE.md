# MyWaveWake — Platform State (canonical snapshot)

**Production:** https://mywavewake.ru  
**Модель:** formal production-governed platform · operational maturity governance  
**Governance index:** [PRODUCTION_GOVERNANCE.md](PRODUCTION_GOVERNANCE.md)  
**Phase:** [deployment/OPERATIONAL_MATURITY_PHASE.md](deployment/OPERATIONAL_MATURITY_PHASE.md)

> Главный актив проекта — **operational governance discipline**. Её необходимо сохранять.

---

## Production status

Production **operational**.

| Компонент | Статус |
|-----------|--------|
| Flask/Gunicorn runtime | operational |
| Redis | operational |
| Google integrations | operational |
| Booking slots | operational |
| Socket.IO | operational |
| Node proxy | operational |
| systemd services | operational |
| Nginx | operational |
| SSL | operational |
| Health endpoints | operational |
| Google Sheets validation | operational |
| Telegram notifications | operational |

Runtime Foundation стабилен = **production infrastructure foundation** (`3de56f8c` FROZEN).

---

## Governance entrypoint

| Документ | Назначение |
|----------|------------|
| [PRODUCTION_GOVERNANCE.md](PRODUCTION_GOVERNANCE.md) | Governance index |
| [deployment/STABILIZATION_QA_PHASE.md](deployment/STABILIZATION_QA_PHASE.md) | Operational scope / P1 / P2 |
| [deployment/RUNTIME_GOVERNANCE.md](deployment/RUNTIME_GOVERNANCE.md) | Runtime freeze / change control |

Все production-решения синхронизируются через эти документы.

---

## Formal runtime governance

| | |
|---|---|
| Frozen baseline | `3de56f8c` |
| Definition | production infrastructure foundation |

Runtime changes **только** через: (1) issue (2) rollback plan (3) smoke strategy (4) production justification (5) explicit approval.

**Без всех пяти: CHANGE REJECTED.**

### Freeze scope

Flask bootstrap · Gunicorn wiring · SQLAlchemy init · Redis architecture · Socket.IO runtime · booking API architecture · Google services init · env loading · health routing · websocket architecture · runtime SSL/DNS patches.

---

## Four-layer model

| Layer | Status |
|-------|--------|
| Runtime Foundation | **FROZEN** |
| Frontend UX | ACTIVE (`48dc9c64`) |
| Content Pipeline | ACTIVE |
| Ops / Observability | ACTIVE |

Изменения между слоями — минимально связаны.

---

## Release discipline

**ОДИН DEPLOY = ОДИН RELEASE TYPE.**

| Type | Scope |
|------|-------|
| `runtime` | backend / runtime / infrastructure |
| `frontend` | CSS / templates / static UX |
| `content` | parser / blog / Sheets visibility |
| `ops` | monitoring / security / deploy |

Смешанные runtime+frontend deploy — **запрещены** без approval.

### Deploy flow

```
Изменение → release type → RELEASE_GATE_CHECKLIST → production_smoke.sh
         → Mobile QA (frontend) → deploy → post-deploy smoke → rollback при FAIL
```

---

## Post-deploy policy

Deploy **НЕЗАВЕРШЁН**, пока нет:

| # | Требование |
|---|------------|
| 1 | Строка в [PRODUCTION_AUDIT_LOG.md](ops/PRODUCTION_AUDIT_LOG.md) |
| 2 | Release note в [releases/](releases/) |
| 3 | `production_smoke.sh` → PASS |
| 4 | Mobile QA (если `frontend`) → [MOBILE_QA_MATRIX.md](qa/MOBILE_QA_MATRIX.md) |

---

## Operational maturity artifacts

| # | Артефакт | Путь |
|---|----------|------|
| 1 | Ownership matrix | [ops/OWNERSHIP_MATRIX.md](ops/OWNERSHIP_MATRIX.md) — **заполнить имена** |
| 2 | Release notes registry | [releases/](releases/) |
| 3 | Environment governance | [deployment/ENVIRONMENT_POLICY.md](deployment/ENVIRONMENT_POLICY.md) |
| 4 | Severity escalation | [ops/SEVERITY_ESCALATION_MATRIX.md](ops/SEVERITY_ESCALATION_MATRIX.md) |
| 5 | Production audit log | [ops/PRODUCTION_AUDIT_LOG.md](ops/PRODUCTION_AUDIT_LOG.md) |

---

## Severity governance

| Severity | Action |
|----------|--------|
| SEV-1 | immediate rollback |
| SEV-2 | deploy freeze |
| SEV-3 | monitored degradation |
| SEV-4 | backlog |

Детали: [SEVERITY_ESCALATION_MATRIX.md](ops/SEVERITY_ESCALATION_MATRIX.md) · [PRODUCTION_INCIDENT_POLICY.md](ops/PRODUCTION_INCIDENT_POLICY.md)

---

## Stabilization execution (текущая работа)

### P1

- Mobile QA matrix  
- Blog visibility  
- Checklist visuals  
- Reviews/static polish  

### P2

- Hardening  
- Observability  
- CI/CD discipline  

**До stabilization exit:** никаких runtime refactor.

---

## Обязательные правила (10)

1. Backend runtime frozen.  
2. Frontend changes only incremental.  
3. Every deploy → smoke.  
4. Every UX deploy → Mobile QA.  
5. No secrets in Git.  
6. No runtime experiments.  
7. No architecture rewrites.  
8. No direct production hotfixes without smoke.  
9. Stability > feature velocity.  
10. Every change must have rollback path.  

---

## Цель

**Exit:** stable · polished · mobile-ready · hardened · observable · investor/demo ready.

**После exit:** SEO · parser scaling · sponsor platform · AI orchestration · tourism ecosystem · advanced analytics · growth automation.

---

## Baselines (reference)

| Layer | Commit | Status |
|-------|--------|--------|
| Runtime Foundation | `3de56f8c` | FROZEN |
| Frontend/docs | `48dc9c64` | ACTIVE |
| Operational maturity pack | `1858292d` | ACTIVE |
| Operational Maturity Phase | `258c4df5` | ACTIVE |
