# MyWaveWake — Platform State

**Production:** https://mywavewake.ru  
**Модель:** formal production-governed platform · engineering maturity phase  
**Roadmap:** [deployment/ENGINEERING_MATURITY_ROADMAP.md](deployment/ENGINEERING_MATURITY_ROADMAP.md)

> **Canonical operational snapshot платформы** — главный документ текущего состояния.  
> **Главный актив платформы:** operational governance discipline (не только runtime).

| Раздел snapshot |
|-----------------|
| production status · governance stack (5 docs) · runtime freeze · four-layer model |
| release discipline · post-deploy policy · operational maturity artifacts |
| severity governance · P1/P2 execution · exit criteria |

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

Deploy **governance-incomplete** / **operationally incomplete** / НЕЗАВЕРШЁН, пока нет:

| # | Требование |
|---|------------|
| 1 | Строка в [PRODUCTION_AUDIT_LOG.md](ops/PRODUCTION_AUDIT_LOG.md) |
| 2 | Release note в [releases/](releases/) |
| 3 | `production_smoke.sh` → PASS |
| 4 | Mobile QA (если `frontend`) → [MOBILE_QA_MATRIX.md](qa/MOBILE_QA_MATRIX.md) |

---

## Operational maturity artifacts (обязательные)

Часть production governance, **не** optional documentation.

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

Rollback обязателен при: health unhealthy · booking failure · restart loops · массовых 5xx · smoke FAIL.

Детали: [SEVERITY_ESCALATION_MATRIX.md](ops/SEVERITY_ESCALATION_MATRIX.md) · [PRODUCTION_INCIDENT_POLICY.md](ops/PRODUCTION_INCIDENT_POLICY.md)

---

## Stabilization execution (текущая работа)

### Текущий приоритет (Phase 1 — BLOCKER)

**Real Mobile QA execution** — [ENGINEERING_MATURITY_ROADMAP.md](deployment/ENGINEERING_MATURITY_ROADMAP.md#phase-1--real-mobile-qa-execution-текущий-blocker)

### P1 (после QA)

- Checklist visuals  
- Reviews/static polish  
- Blog visibility  

### P2

- Hardening  
- Observability  
- CI/CD discipline  

**До stabilization exit:** никаких runtime refactor.

### Operational pack (интегрирован 2026-05-15)

| Commit | Содержание |
|--------|------------|
| `0d07eee7` | ownership matrix + Mobile QA run |
| `544f518a` | refs / audit sync |

Release note: [releases/2026-05-15-operational-pack-ownership-qa.md](releases/2026-05-15-operational-pack-ownership-qa.md)

| Артефакт | Статус |
|----------|--------|
| [OWNERSHIP_MATRIX.md](ops/OWNERSHIP_MATRIX.md) | **filled** — follow-up: реальные имена + contacts |
| [MOBILE_QA_RUN_2026-05-15.md](qa/MOBILE_QA_RUN_2026-05-15.md) | **PENDING** — device run required |
| [MOBILE_QA_MATRIX.md](qa/MOBILE_QA_MATRIX.md) | sign-off **NO** до PASS |

**Зрелость платформы сейчас:** deploy discipline · quality gates · audit traceability · ownership clarity · rollback readiness · execution consistency.

### Следующие практические шаги (blocking)

1. **Mobile QA execution** — A1/A2/I1/T1 на https://mywavewake.ru → screenshots → PASS/FAIL → sign-off YES  
2. Заменить temporary roles в [OWNERSHIP_MATRIX.md](ops/OWNERSHIP_MATRIX.md)  
3. P2 hardening на сервере  
4. Audit log + release notes на каждый deploy  

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
| Platform state canon | `1ad1427c` | ACTIVE |
| Governance stack canon | `2a8a5256` | ACTIVE |
| Operational pack | `0d07eee7` / `544f518a` | ACTIVE |
