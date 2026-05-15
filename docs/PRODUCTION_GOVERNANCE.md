# MyWaveWake — Production Governance

**Production:** https://mywavewake.ru  
**Модель:** production-governed система с **formal runtime governance**  
**Слои:** runtime · UX · content · ops

> **Этот файл — канонический governance entrypoint.**  
> Детальный operational scope: [deployment/STABILIZATION_QA_PHASE.md](deployment/STABILIZATION_QA_PHASE.md)  
> Formal runtime rules: [deployment/RUNTIME_GOVERNANCE.md](deployment/RUNTIME_GOVERNANCE.md)

Все production-решения синхронизируются через эти документы.

---

## Production статус

Production **operational**. Runtime стабилен.

| Компонент | Статус |
|-----------|--------|
| Flask/Gunicorn runtime | operational |
| Redis | operational |
| Google integrations | operational |
| Booking | operational |
| Socket.IO | operational |
| Node proxy | operational |
| systemd | operational |
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

---

## Главное правило

**Runtime Foundation заморожен на `3de56f8c`.**

Runtime = production infrastructure foundation.

Любые runtime changes:

- только через отдельный issue  
- только с rollback plan  
- только со smoke strategy  
- только с production justification  

Freeze scope: [RUNTIME_GOVERNANCE.md](deployment/RUNTIME_GOVERNANCE.md)

---

## Канонические governance-документы

| Документ | Путь | Назначение |
|----------|------|------------|
| **Governance index** | `docs/PRODUCTION_GOVERNANCE.md` | этот файл |
| Stabilization scope | [STABILIZATION_QA_PHASE.md](deployment/STABILIZATION_QA_PHASE.md) | P1/P2, exit criteria |
| Runtime governance | [RUNTIME_GOVERNANCE.md](deployment/RUNTIME_GOVERNANCE.md) | freeze, change control |
| UX/mobile | [FRONTEND_POLISH_PHASE.md](deployment/FRONTEND_POLISH_PHASE.md) | frontend scope |
| Mobile QA | [MOBILE_QA_MATRIX.md](qa/MOBILE_QA_MATRIX.md) | PASS/FAIL matrix |
| Blog content | [BLOG_CONTENT_VISIBILITY.md](deployment/BLOG_CONTENT_VISIBILITY.md) | visibility rules |
| Incidents | [PRODUCTION_INCIDENT_POLICY.md](ops/PRODUCTION_INCIDENT_POLICY.md) | SEV / rollback |
| Release gate | [RELEASE_GATE_CHECKLIST.md](deployment/RELEASE_GATE_CHECKLIST.md) | pre-deploy gate |
| Release types | [RELEASE_TYPES.md](deployment/RELEASE_TYPES.md) | taxonomy |
| Server ops | [TIMEWEB_PRODUCTION_RUNBOOK.md](deployment/TIMEWEB_PRODUCTION_RUNBOOK.md) | Timeweb ops |
| Rollback | [POST_DEPLOY_ROLLBACK.md](deployment/POST_DEPLOY_ROLLBACK.md) | known-good commits |

---

## Release taxonomy

**ОДИН DEPLOY = ОДИН RELEASE TYPE.**

| Type | Scope |
|------|-------|
| `runtime` | backend / infrastructure |
| `frontend` | CSS / templates / UX |
| `content` | parser / blog / Sheets |
| `ops` | monitoring / security / deploy |

Смешанные **runtime + UX** deploy запрещены без отдельного approval.

---

## Канонический deploy flow

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

Скрипты: `scripts/production_smoke.sh`, `scripts/healthcheck.sh`

---

## P1 — текущие приоритеты

### Frontend UX (baseline `48dc9c64`)

mobile stability · swipe UX · typography · safe-area · touch ergonomics · no horizontal scroll · no clipped cards · readable forms · stable carousels

QA: [MOBILE_QA_MATRIX.md](qa/MOBILE_QA_MATRIX.md) — Android Chrome, Yandex, iPhone Safari, Tablet.

### Blog content pipeline

Routing/runtime стабилен. Visibility: statuses, parser sync, slug, Sheets mapping, cache invalidation.

**`APPROVED` ≠ visible post.** Нужно: `READY_TO_PUBLISH` или `PUBLISHED`.  
Не: routing rewrite, runtime refactor, template architecture rewrite.

### Checklist visuals

Placeholder webp → финальные иллюстрации, art direction, optimized assets.  
Не менять: rendering logic, asset routing, template structure.

### Static / reviews

image optimization · nginx static cache · responsive avatars · eager/lazy loading · mobile consistency

---

## P2 — hardening & maturity

**Hardening:** fail2ban, UFW, logrotate, backup cron, Redis persistence, gzip/cache, certbot, nginx rate limiting, Telegram alerts, uptime/disk/log monitoring.

**Observability:** production_smoke.sh, healthcheck.sh, release smoke discipline, rollback validation, alerts.

**CI/CD:** release tagging, deploy/rollback reproducibility, environment isolation, release notes, secrets hygiene, release cadence.

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

## Stabilization phase goal

**Exit:** stable · polished · mobile-ready · hardened · observable · investor/demo ready.

**После exit:** SEO, parser scaling, sponsor platform, AI orchestration, tourism ecosystem, advanced analytics, growth automation.

**До exit:** никаких runtime refactor.
