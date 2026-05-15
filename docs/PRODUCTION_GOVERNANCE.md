# MyWaveWake — Production Governance

**Платформа:** formal production-governed platform  
**Модель:** runtime governance · release discipline · stabilization execution · **operational maturity**  
**Фаза:** **Operational Maturity Phase**  
**Phase doc:** [deployment/OPERATIONAL_MATURITY_PHASE.md](deployment/OPERATIONAL_MATURITY_PHASE.md)  
**Production:** https://mywavewake.ru

> Главный актив проекта — **operational governance discipline**. Её необходимо сохранять.

## Каноническая тройка governance

| Документ | Назначение |
|----------|------------|
| **`docs/PRODUCTION_GOVERNANCE.md`** | Governance entrypoint (этот файл) |
| [deployment/STABILIZATION_QA_PHASE.md](deployment/STABILIZATION_QA_PHASE.md) | Operational scope / P1 / P2 / execution |
| [deployment/RUNTIME_GOVERNANCE.md](deployment/RUNTIME_GOVERNANCE.md) | Runtime freeze / change control |

Все production-решения синхронизируются **только** через эти три документа.

---

## Production status

Production **operational**. Runtime стабилен = **infrastructure foundation**.

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

---

## Канонические baselines

| Layer | Commit | Status |
|-------|--------|--------|
| Runtime Foundation | `3de56f8c` | **FROZEN** |
| Frontend/docs | `48dc9c64` | ACTIVE |
| QA/Ops governance | `0a2a0e1a` | ACTIVE |
| Production state/docs | `94fbc211` | ACTIVE |
| Governance index | `4d1ded82` | ACTIVE |
| Formal runtime governance | `30f991da` | ACTIVE |
| Phase transition canon | `56b98c49` | ACTIVE |
| Platform canon | `15ee2680` | ACTIVE |
| Operational maturity pack | `1858292d` | ACTIVE |

---

## Post-deploy (обязательно)

Deploy **незавершён**, пока не выполнено:

1. Строка в [PRODUCTION_AUDIT_LOG.md](ops/PRODUCTION_AUDIT_LOG.md)  
2. Release note в [releases/](releases/)  
3. `production_smoke.sh` → PASS  
4. Mobile QA (если `frontend`) → [MOBILE_QA_MATRIX.md](qa/MOBILE_QA_MATRIX.md)  

---

## Operational maturity артефакты

| Артефакт | Путь | Назначение |
|----------|------|------------|
| Ownership matrix | [ops/OWNERSHIP_MATRIX.md](ops/OWNERSHIP_MATRIX.md) | Zone owners |
| Severity escalation | [ops/SEVERITY_ESCALATION_MATRIX.md](ops/SEVERITY_ESCALATION_MATRIX.md) | SEV → action |
| Production audit log | [ops/PRODUCTION_AUDIT_LOG.md](ops/PRODUCTION_AUDIT_LOG.md) | Deploy history |
| Environment policy | [deployment/ENVIRONMENT_POLICY.md](deployment/ENVIRONMENT_POLICY.md) | local / staging / prod |
| Release notes registry | [releases/](releases/) | Audit trail, onboarding |

---

## Four-layer model

Изменения между слоями **минимально связаны**.

| # | Слой | Baseline | Статус |
|---|------|----------|--------|
| 1 | **Runtime Foundation** | `3de56f8c` | FROZEN |
| 2 | **Frontend UX** | `48dc9c64` | ACTIVE |
| 3 | **Content Pipeline** | Sheets / parser | ACTIVE (data) |
| 4 | **Ops / Observability** | runbooks + scripts | ACTIVE |

---

## Formal runtime governance

**Runtime Foundation baseline:** `3de56f8c`  
Runtime Foundation = production infrastructure foundation.

Любые runtime changes допускаются только через:

1. отдельный issue  
2. rollback plan  
3. smoke strategy  
4. production justification  
5. explicit approval  

**Без всех пяти пунктов: CHANGE REJECTED.**

### Freeze scope

Без explicit approval не изменяются:

- Flask bootstrap  
- Gunicorn wiring  
- SQLAlchemy init  
- Redis architecture  
- Socket.IO runtime  
- booking API architecture  
- Google services init  
- env loading  
- health routing  
- websocket architecture  
- runtime SSL/DNS patches  

Полный регламент: [RUNTIME_GOVERNANCE.md](deployment/RUNTIME_GOVERNANCE.md)

---

## Release discipline

**ОДИН DEPLOY = ОДИН RELEASE TYPE.**

| Type | Scope |
|------|-------|
| `runtime` | backend / infrastructure |
| `frontend` | CSS / templates / UX |
| `content` | parser / blog / Sheets |
| `ops` | monitoring / security / deploy |

Смешанные **runtime + UX** deploy запрещены без отдельного approval.  
Детали: [RELEASE_TYPES.md](deployment/RELEASE_TYPES.md)

---

## Deploy flow

```
Изменение
  → release type classification
  → RELEASE_GATE_CHECKLIST
  → production_smoke.sh
  → Mobile QA (если frontend)
  → deploy
  → post-deploy smoke
  → rollback при FAIL
```

| Скрипт | Назначение |
|--------|------------|
| `scripts/production_smoke.sh` | post-deploy HTTP smoke |
| `scripts/healthcheck.sh` | health / watchdog |

Gate: [RELEASE_GATE_CHECKLIST.md](deployment/RELEASE_GATE_CHECKLIST.md)

---

## Stabilization execution model

**До exit criteria:** никаких runtime refactor.

### P1 — execute now

| Track | Действие | Артефакт |
|-------|----------|----------|
| Frontend UX | mobile-first incremental CSS/templates | [MOBILE_QA_MATRIX.md](qa/MOBILE_QA_MATRIX.md) |
| Blog content | statuses, parser, slug, Sheets, cache | [BLOG_CONTENT_VISIBILITY.md](deployment/BLOG_CONTENT_VISIBILITY.md) |
| Checklist visuals | финальные webp (не logic/routing) | design assets |
| Static / reviews | avatars, cache, lazy/eager | nginx `/static/` |

**Frontend UX baseline:** `48dc9c64` — mobile stability, swipe UX, safe-area, typography, touch ergonomics, no horizontal scroll, stable carousels, readable forms.

**Blog:** `APPROVED` ≠ visible. Нужно `READY_TO_PUBLISH` или `PUBLISHED`. Не: routing/runtime/template architecture rewrite.

**Checklist:** placeholder webp → art direction + optimized assets. Не менять rendering logic, asset routing, template structure.

### P2 — hardening & maturity

| Track | Items |
|-------|-------|
| Hardening | fail2ban, UFW, logrotate, backup cron, Redis persistence, gzip/cache, certbot, nginx rate limit, Telegram alerts, uptime/disk/log monitoring |
| Observability | production_smoke.sh, healthcheck.sh, release smoke, rollback validation, alerts |
| CI/CD | release tagging, deploy/rollback reproducibility, env isolation, release notes, secrets hygiene, cadence |

Полный чеклист: [STABILIZATION_QA_PHASE.md](deployment/STABILIZATION_QA_PHASE.md)

---

## Supporting governance docs

| Документ | Путь |
|----------|------|
| UX scope | [FRONTEND_POLISH_PHASE.md](deployment/FRONTEND_POLISH_PHASE.md) |
| Incidents | [PRODUCTION_INCIDENT_POLICY.md](ops/PRODUCTION_INCIDENT_POLICY.md) |
| Severity matrix | [SEVERITY_ESCALATION_MATRIX.md](ops/SEVERITY_ESCALATION_MATRIX.md) |
| Ownership | [OWNERSHIP_MATRIX.md](ops/OWNERSHIP_MATRIX.md) |
| Environments | [ENVIRONMENT_POLICY.md](deployment/ENVIRONMENT_POLICY.md) |
| Audit log | [PRODUCTION_AUDIT_LOG.md](ops/PRODUCTION_AUDIT_LOG.md) |
| Releases | [releases/README.md](releases/README.md) |
| Server ops | [TIMEWEB_PRODUCTION_RUNBOOK.md](deployment/TIMEWEB_PRODUCTION_RUNBOOK.md) |
| Rollback | [POST_DEPLOY_ROLLBACK.md](deployment/POST_DEPLOY_ROLLBACK.md) |

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

## Rollback policy

| Layer | Rollback |
|-------|----------|
| Frontend | revert UX commit |
| Runtime | rollback to `3de56f8c` |

Обязателен при: health unhealthy, booking failure, restart loops, массовых 5xx, smoke FAIL.

---

## Current stabilization goal

**Exit criteria:** stable · polished · mobile-ready · hardened · observable · investor/demo ready.

**После exit:** SEO, parser scaling, sponsor platform, AI orchestration, tourism ecosystem, advanced analytics, growth automation.

**До exit:** никаких runtime refactor.
