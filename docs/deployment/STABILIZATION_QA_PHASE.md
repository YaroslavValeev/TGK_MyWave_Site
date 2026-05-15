# Production Stabilization + QA Discipline

**Платформа:** formal production-governed · operational maturity  
**Фаза:** [Operational Maturity Phase](OPERATIONAL_MATURITY_PHASE.md) (stabilization execution продолжается)  
**Snapshot:** [PLATFORM_STATE.md](../PLATFORM_STATE.md)  
**Governance index:** [PRODUCTION_GOVERNANCE.md](../PRODUCTION_GOVERNANCE.md)  
**Runtime rules:** [RUNTIME_GOVERNANCE.md](RUNTIME_GOVERNANCE.md)  
**Phase:** [OPERATIONAL_MATURITY_PHASE.md](OPERATIONAL_MATURITY_PHASE.md)  
**Дата фиксации:** 2026-05  
**Production:** https://mywavewake.ru  
**Статус:** production operational, runtime = infrastructure foundation.

---

## Текущее production состояние

### Инфраструктура

| Компонент | Стек |
|-----------|------|
| OS | Ubuntu 22.04 |
| Cloud | Timeweb Cloud — 2 CPU / 4 GB RAM / 50 GB NVMe |
| Edge | Nginx + SSL |
| App | Flask + Gunicorn + eventlet |
| Cache / realtime | Redis, Socket.IO |
| Integrations | Google Sheets / Calendar / Drive, Telegram bots |
| Proxy | Node compatibility proxy |
| Process manager | systemd |

### Подтверждено operational

- Flask/Gunicorn runtime  
- Redis  
- Google integrations  
- Booking slots  
- Socket.IO  
- Node proxy  
- systemd, Nginx, SSL  
- Health endpoints  
- Google Sheets validation  
- Slots API  
- Telegram notifications  

---

## Канонические baselines

| Слой | Commit | Статус |
|------|--------|--------|
| **Runtime Foundation** | `3de56f8c` | **FROZEN** |
| **Frontend/docs** | `48dc9c64` | ACTIVE |
| **QA/Ops governance** | `0a2a0e1a` | ACTIVE |
| **Production state/docs** | `94fbc211` | ACTIVE |
| **Governance index** | `4d1ded82` | ACTIVE |
| **Formal runtime governance** | `30f991da` | ACTIVE |

**Runtime Foundation** = production infrastructure foundation. Любое изменение runtime:

- отдельный issue  
- rollback plan  
- smoke strategy  
- production justification  
- explicit approval  

---

## Канонические документы

Все production-действия опираются на эти файлы:

| Документ | Путь | Назначение |
|----------|------|------------|
| Governance index | [PRODUCTION_GOVERNANCE.md](../PRODUCTION_GOVERNANCE.md) | Entrypoint |
| Runtime governance | [RUNTIME_GOVERNANCE.md](RUNTIME_GOVERNANCE.md) | Formal freeze / change control |
| Stabilization governance | [STABILIZATION_QA_PHASE.md](STABILIZATION_QA_PHASE.md) | Этот документ — фаза, baselines, P1/P2 |
| UX/mobile scope | [FRONTEND_POLISH_PHASE.md](FRONTEND_POLISH_PHASE.md) | Frontend polish, CSS paths |
| Mobile QA | [MOBILE_QA_MATRIX.md](../qa/MOBILE_QA_MATRIX.md) | PASS/FAIL matrix |
| Blog content | [BLOG_CONTENT_VISIBILITY.md](BLOG_CONTENT_VISIBILITY.md) | Visibility без routing |
| Incidents | [PRODUCTION_INCIDENT_POLICY.md](../ops/PRODUCTION_INCIDENT_POLICY.md) | Severity, rollback, freeze |
| Server ops | [TIMEWEB_PRODUCTION_RUNBOOK.md](TIMEWEB_PRODUCTION_RUNBOOK.md) | Deploy, hardening |
| Release gate | [RELEASE_GATE_CHECKLIST.md](RELEASE_GATE_CHECKLIST.md) | Gate перед prod |
| Release types | [RELEASE_TYPES.md](RELEASE_TYPES.md) | runtime / frontend / ops / content |
| Rollback | [POST_DEPLOY_ROLLBACK.md](POST_DEPLOY_ROLLBACK.md) | Known-good commits |

---

## Главное правило: RUNTIME FOUNDATION ЗАМОРОЖЕН

Baseline: `3de56f8c`. Без explicit approval области ниже **не изменяются**.

### Что считается Runtime Foundation (freeze scope)

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
- runtime SSL / DNS patches  

### Нельзя

- runtime refactor  
- async rewrites  
- migration chaos  
- architecture experiments  
- «quick fixes» напрямую в production  

---

## Четыре независимых слоя

Изменения между слоями **минимально связаны**.

```
┌─────────────────────┐
│ 1. Runtime Foundation│  ← FROZEN (3de56f8c)
├─────────────────────┤
│ 2. Frontend UX       │  ← ACTIVE (48dc9c64+)
├─────────────────────┤
│ 3. Content Pipeline  │  ← Sheets / parser / statuses
├─────────────────────┤
│ 4. Ops/Observability │  ← hardening, smoke, alerts
└─────────────────────┘
```

---

## Текущая фаза — приоритеты

| # | Область |
|---|---------|
| 1 | Frontend UX polish |
| 2 | Mobile stability |
| 3 | Content pipeline |
| 4 | Production hardening |
| 5 | Observability |
| 6 | Release discipline |

**НЕ делаем:** новые backend features, архитектурные изменения, runtime optimization experiments.

---

## P1 — Frontend UX polish

**Active baseline:** `48dc9c64`

Уже внедрено:

- `mobile-home.css` v3  
- swipe carousel UX  
- hero compact layout  
- safe-area handling  
- contacts layout fixes  
- reviews responsive avatars  
- checklist mobile layout  

**Mobile QA:** [MOBILE_QA_MATRIX.md](../qa/MOBILE_QA_MATRIX.md) — платформы A1, A2, I1, T1.

Критерии: no horizontal scroll, no clipped cards, typography, touch ≥ 44px, forms, safe-area, no CTA overlap.

---

## P1 — Blog content pipeline

Routing стабилен. **Backend routing/runtime не трогать.**

Visibility через: statuses, parser sync, Sheets mapping, slug, cache invalidation.

См. [BLOG_CONTENT_VISIBILITY.md](BLOG_CONTENT_VISIBILITY.md).

**`APPROVED` ≠ visible post.** Для отображения: `READY_TO_PUBLISH` или `PUBLISHED`.

---

## P1 — Checklist visuals

Placeholder webp → финальные иллюстрации, art direction, optimized webp.

**Не менять:** asset routing, rendering logic, template structure.

---

## P1 — Static / reviews

- responsive avatars  
- image optimization  
- eager/lazy loading  
- nginx static cache  
- mobile rendering consistency  

---

## P2 — Production hardening

Завершить на сервере (см. [TIMEWEB_PRODUCTION_RUNBOOK.md](TIMEWEB_PRODUCTION_RUNBOOK.md)):

- [ ] fail2ban  
- [ ] UFW  
- [ ] logrotate  
- [ ] backup cron  
- [ ] Redis persistence  
- [ ] gzip/cache tuning  
- [ ] certbot auto-renew  
- [ ] nginx rate limiting  
- [ ] monitoring  
- [ ] Telegram alerts  
- [ ] uptime checks  
- [ ] health watchdog  
- [ ] disk monitoring  

---

## P2 — Observability

- `scripts/production_smoke.sh`  
- `scripts/healthcheck.sh`  
- release smoke discipline  
- rollback validation  
- monitoring alerts  

---

## P2 — CI/CD discipline

- release tagging  
- deploy / rollback reproducibility  
- environment separation  
- secrets hygiene  
- release notes policy  

Типы релизов: [RELEASE_TYPES.md](RELEASE_TYPES.md).

---

## Обязательные правила работы

1. Backend runtime frozen.  
2. Frontend changes only incremental.  
3. Every deploy → smoke.  
4. Every UX change → Mobile QA.  
5. No secrets in Git.  
6. No runtime experiments.  
7. No architecture rewrites.  
8. No direct hotfixes in production.  
9. Production stability > feature velocity.  
10. Любое изменение → rollback path.  

---

## Release taxonomy

**ОДИН DEPLOY = ОДИН RELEASE TYPE.** См. [RELEASE_TYPES.md](RELEASE_TYPES.md).

| Type | Scope |
|------|-------|
| `runtime` | backend / runtime / infrastructure |
| `frontend` | CSS / templates / static UX |
| `content` | blog / parser / Sheets visibility |
| `ops` | monitoring / security / deploy |

Запрещено: смешанный **runtime + UX** hotfix deploy без отдельного approval.

---

## Рабочий deploy flow

```
Изменение
  → классификация release type (один тип на deploy)
  → RELEASE_GATE_CHECKLIST
  → production_smoke.sh
  → Mobile QA (если frontend)
  → deploy
  → post-deploy smoke
  → rollback при FAIL
```

---

## Rollback

| Layer | Strategy |
|-------|----------|
| Frontend | revert UX commit |
| Backend | rollback к `3de56f8c` |

**Немедленный rollback runtime** при:

- health unhealthy (core)  
- booking 5xx  
- Gunicorn instability  
- restart loops  
- массовых 5xx  

См. [PRODUCTION_INCIDENT_POLICY.md](../ops/PRODUCTION_INCIDENT_POLICY.md), [POST_DEPLOY_ROLLBACK.md](POST_DEPLOY_ROLLBACK.md).

---

## Цель фазы (exit criteria)

- [ ] Mobile QA — все платформы PASS  
- [ ] Release gate на каждом deploy  
- [ ] P2 hardening завершён  
- [ ] Blog visible content (content layer)  
- [ ] Checklist — финальные webp  
- [ ] Demo / investor ready  

**После stabilization:** SEO, parser scaling, sponsor platform, AI orchestration, tourism ecosystem, advanced analytics, growth automation.

**До exit:** никаких runtime refactor.

---

## История commits

| Commit | Назначение |
|--------|------------|
| `68b46537` | Timeweb prod baseline |
| `3de56f8c` | **Frozen runtime** |
| `48dc9c64` | Frontend/docs — mobile v3, smoke |
| `0a2a0e1a` | QA/Ops governance artifacts |
| `94fbc211` | Production state / canonical governance docs |
| `4d1ded82` | Governance index + release taxonomy canon |
| `30f991da` | Formal runtime governance canon |
| `56b98c49` | Phase transition canon |
| `15ee2680` | Platform canon + execution model |

### Operational maturity (P2 governance)

- [OWNERSHIP_MATRIX.md](../ops/OWNERSHIP_MATRIX.md)  
- [SEVERITY_ESCALATION_MATRIX.md](../ops/SEVERITY_ESCALATION_MATRIX.md)  
- [PRODUCTION_AUDIT_LOG.md](../ops/PRODUCTION_AUDIT_LOG.md)  
- [ENVIRONMENT_POLICY.md](ENVIRONMENT_POLICY.md)  
- [releases/](../releases/)  
