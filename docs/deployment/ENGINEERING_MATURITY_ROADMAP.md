# Engineering Maturity Roadmap — MyWaveWake

**Status:** accepted and integrated in platform governance  
**Canon commit:** `af153b05`  
**Production:** https://mywavewake.ru  
**Runtime baseline:** `3de56f8c` (**FROZEN**) — operationally stable  

**Integrated in:** [PLATFORM_STATE.md](../PLATFORM_STATE.md) · [PRODUCTION_GOVERNANCE.md](../PRODUCTION_GOVERNANCE.md) · [docs/README.md](../README.md)

После синхронизации governance stack платформа в **engineering maturity phase**.

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

**Status:** `IN PROGRESS — BLOCKER` · living doc: [PHASE1_MOBILE_QA_STATUS.md](../qa/PHASE1_MOBILE_QA_STATUS.md)

**Главный приоритет платформы.** До завершения: frontend release = **governance-incomplete**.

### Step 0 — Deploy mobile v3 to production (сейчас)

Prod HTML: `?v=2` → нужен `?v=3`. **Frontend release**, не runtime.

```bash
cd /var/www/mywave && git pull --ff-only origin main
grep mobile-home templates/base.html
sudo systemctl reload mywave-site
curl -sS https://mywavewake.ru/ | grep mobile-home
bash scripts/qa_mobile_precheck.sh && bash scripts/production_smoke.sh
```

Precheck: `000a7100` · [MOBILE_QA_AUTOMATED_PRECHECK_2026-05-15.md](../qa/MOBILE_QA_AUTOMATED_PRECHECK_2026-05-15.md)

### Step 1 — Manual device QA (после `?v=3`)

### Platforms (обязательно)

| Platform |
|----------|
| Android Chrome |
| Android Yandex |
| iPhone Safari |
| Tablet |

### Execution checklist

- [ ] инкогнито / private mode  
- [ ] hard refresh  
- [ ] `mobile-home.css?v=3` в Network  

### Что проверяем

hero · carousel/cards · contacts · chat widget · checklist · reviews · safe-area · tablet responsiveness · spacing consistency · visual clipping · overlay correctness

### Артефакты

| Действие | Файл |
|----------|------|
| Device run | [MOBILE_QA_RUN_2026-05-15.md](../qa/MOBILE_QA_RUN_2026-05-15.md) |
| Matrix | [MOBILE_QA_MATRIX.md](../qa/MOBILE_QA_MATRIX.md) |
| Screenshots | `docs/qa/screenshots/2026-05-15/*.png` |

Заменить `PENDING` → `PASS` / `FAIL`. После завершения: **Ready for release gate: YES**.

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

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Real Mobile QA execution | **IN PROGRESS — BLOCKER** — Step 0: deploy `?v=3`; Step 1: device QA |
| 2 | P1 visual polish | pending (after QA) |
| 3 | P2 hardening | pending |
| 4 | Operational maturity | partial |

## Критерии зрелости (текущий фокус)

Не количество новых функций, а:

- predictable deploys  
- rollback confidence  
- audit traceability  
- ownership clarity  
- QA consistency  
- operational execution discipline  
