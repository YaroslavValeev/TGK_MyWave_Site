# Engineering Maturity Roadmap — MyWaveWake

**Production:** https://mywavewake.ru  
**Runtime baseline:** `3de56f8c` (**FROZEN**) — operationally stable  
**Governance:** [PRODUCTION_GOVERNANCE.md](../PRODUCTION_GOVERNANCE.md) · [PLATFORM_STATE.md](../PLATFORM_STATE.md)  
**Phase context:** [OPERATIONAL_MATURITY_PHASE.md](OPERATIONAL_MATURITY_PHASE.md)

После синхронизации governance stack и стабилизации production runtime платформа переходит в **engineering maturity phase**.

> Приоритет **не** — новые функции любой ценой.  
> Приоритет — reproducible deploys, predictable releases, rollback confidence, observability, QA consistency, ownership accountability, operational execution discipline.

---

## Главный актив

**Operational governance discipline** — не только код.

Она снижает риск production failures, делает deploy предсказуемым, обеспечивает rollback readiness, позволяет масштабировать платформу дальше.

---

## Runtime (без изменений)

| | |
|---|---|
| Baseline | `3de56f8c` |
| Status | **FROZEN** |
| Role | production infrastructure foundation — стабильный и предсказуемый |

5-point control: issue · rollback · smoke · justification · approval → иначе **CHANGE REJECTED**.

---

## Phase 1 — REAL MOBILE QA EXECUTION (текущий BLOCKER)

**Главный приоритет.** Frontend deploy = **governance-incomplete** до закрытия.

| Действие | Артефакт |
|----------|----------|
| Device-runs A1/A2/I1/T1 | [MOBILE_QA_RUN_2026-05-15.md](../qa/MOBILE_QA_RUN_2026-05-15.md) |
| PASS/FAIL + screenshots | [MOBILE_QA_MATRIX.md](../qa/MOBILE_QA_MATRIX.md) · `docs/qa/screenshots/2026-05-15/` |
| Sign-off YES | Ready for release gate |

**URL:** https://mywavewake.ru — инкогнито, `mobile-home.css?v=3`

**Критические зоны:** hero · carousel/cards · contacts · chat widget · checklist · reviews · spacing/safe-area · tablet responsiveness

**После QA:** обновить matrix → sign-off → снять frontend governance-incomplete.

---

## Phase 2 — P1 VISUAL POLISH

**После** Mobile QA PASS.

| Track | Действие | Ограничение |
|-------|----------|-------------|
| Checklist visuals | финальные webp вместо placeholder | не менять routing/rendering |
| Reviews/static | avatars, spacing, typography, mobile readability | frontend release only |
| Blog visibility | READY_TO_PUBLISH / PUBLISHED, slug, preview | [BLOG_CONTENT_VISIBILITY.md](BLOG_CONTENT_VISIBILITY.md) — **не** routing/runtime |

Release type: `frontend` / `content` — отдельно от runtime.

---

## Phase 3 — P2 HARDENING

**После** закрытия UX/QA.

### Security

fail2ban · UFW · backup rotation · access review

### Observability

smoke cadence · cron monitoring · alert discipline · health monitoring

Скрипты: `scripts/production_smoke.sh`, `scripts/healthcheck.sh`

### CI/CD discipline

release tagging · release notes cadence · audit consistency · rollback rehearsal

Runbook: [TIMEWEB_PRODUCTION_RUNBOOK.md](TIMEWEB_PRODUCTION_RUNBOOK.md)

Release type: `ops`

---

## Phase 4 — OPERATIONAL MATURITY (post-stabilization execution)

### Ownership maturity

- убрать temporary ownership  
- реальные контакты ([OWNERSHIP_MATRIX.md](../ops/OWNERSHIP_MATRIX.md))  
- escalation ownership · infra accountability  

### Release maturity

- стабильный release cadence  
- predictable deploy windows  
- [PRODUCTION_AUDIT_LOG.md](../ops/PRODUCTION_AUDIT_LOG.md) на каждый deploy  

### Incident maturity

- rollback confidence  
- [SEVERITY_ESCALATION_MATRIX.md](../ops/SEVERITY_ESCALATION_MATRIX.md)  
- production recovery readiness  

---

## Чего НЕ делаем до stabilization exit

- runtime refactor  
- архитектурные эксперименты  
- backend rewrites  
- infra migrations  
- mixed runtime+frontend deploys  
- aggressive optimization  

---

## После stabilization exit

SEO expansion · parser scaling · sponsor platform · AI layers · advanced analytics · scaling architecture · automation expansion

---

## Post-deploy policy (все фазы)

Deploy незавершён без:

1. [PRODUCTION_AUDIT_LOG.md](../ops/PRODUCTION_AUDIT_LOG.md)  
2. Release note в [releases/](../releases/)  
3. `production_smoke.sh` → PASS  
4. Mobile QA PASS (если `frontend`)  

Gate: [RELEASE_GATE_CHECKLIST.md](RELEASE_GATE_CHECKLIST.md)

---

## Server (docs-only)

```bash
cd /var/www/mywave
git fetch origin
git pull --ff-only origin main
git rev-parse HEAD
```

Gunicorn/runtime **не** перезапускать без runtime-release.

---

## Progress tracker

| Phase | Status |
|-------|--------|
| 1 — Mobile QA | **IN PROGRESS** (PENDING device run) |
| 2 — P1 visual polish | blocked |
| 3 — P2 hardening | pending |
| 4 — Operational maturity | partial (ownership filled, contacts TBD) |
