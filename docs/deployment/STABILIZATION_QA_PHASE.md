# Production Stabilization + QA Discipline

**Дата фиксации:** 2026-05  
**Цель:** стабильность runtime при UX-polish; управляемые deploy и инциденты.

---

## Baselines

| Слой | Commit | Роль |
|------|--------|------|
| Runtime Foundation | `3de56f8c` | Frozen backend — Flask, Redis, health, booking, Google, Socket.IO |
| Frontend / docs | `48dc9c64` | Mobile v3, runbooks, production smoke |

Production: https://mywavewake.ru — runtime stable, integrations operational.

---

## Четыре независимых слоя

Изменения между слоями **минимально связаны**.

```
┌─────────────────────┐
│ 1. Runtime Foundation│  ← FROZEN (3de56f8c)
├─────────────────────┤
│ 2. Frontend UX       │  ← mobile-first, incremental CSS/templates
├─────────────────────┤
│ 3. Content Pipeline  │  ← Sheets, statuses, parser — не routing
├─────────────────────┤
│ 4. Ops/Observability │  ← hardening, smoke, alerts, backup
└─────────────────────┘
```

| Слой | Документ / артефакт |
|------|---------------------|
| 1. Runtime | [FRONTEND_POLISH_PHASE.md](FRONTEND_POLISH_PHASE.md) § Backend frozen |
| 2. Frontend UX | [MOBILE_QA_MATRIX.md](../qa/MOBILE_QA_MATRIX.md), `static/css/mobile-home.css` |
| 3. Content | [BLOG_CONTENT_VISIBILITY.md](BLOG_CONTENT_VISIBILITY.md) |
| 4. Ops | [TIMEWEB_PRODUCTION_RUNBOOK.md](TIMEWEB_PRODUCTION_RUNBOOK.md), [PRODUCTION_INCIDENT_POLICY.md](../ops/PRODUCTION_INCIDENT_POLICY.md) |

---

## Обязательные артефакты QA / Ops

| ID | Артефакт | Назначение |
|----|----------|------------|
| A | [MOBILE_QA_MATRIX.md](../qa/MOBILE_QA_MATRIX.md) | Device × browser × section |
| B | [PRODUCTION_INCIDENT_POLICY.md](../ops/PRODUCTION_INCIDENT_POLICY.md) | Severity, rollback, freeze, alerts |
| C | [RELEASE_GATE_CHECKLIST.md](RELEASE_GATE_CHECKLIST.md) | Gate перед prod deploy |

---

## Обязательные правила

1. Backend runtime frozen.  
2. Frontend — только incremental.  
3. No direct hotfixes in production.  
4. Every deploy → `production_smoke.sh`.  
5. Every UX change → Mobile QA matrix.  
6. No secret leakage.  
7. No runtime experiments.  
8. No architecture rewrites.  
9. Production first.  
10. Stability above feature velocity.

---

## Цель фазы (exit criteria)

- [ ] Mobile QA matrix — все платформы PASS  
- [ ] Release gate используется на каждом deploy  
- [ ] P2 hardening применён (fail2ban, UFW, backup, alerts)  
- [ ] Blog visible content (content layer, не routing)  
- [ ] Checklist — финальные webp (design)  
- [ ] Demo / investor ready

**После exit:** SEO, sponsor platform, AI orchestration, parser scaling, tourism ecosystem, analytics.

**До exit:** никаких runtime refactor.

---

## История commits

| Commit | Назначение |
|--------|------------|
| `3de56f8c` | Frozen runtime |
| `48dc9c64` | Frontend polish phase pack |
