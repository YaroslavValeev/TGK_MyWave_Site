# Operational Maturity Phase — MyWaveWake

**Production:** https://mywavewake.ru  
**Дата входа в фазу:** 2026-05  
**Governance index:** [PRODUCTION_GOVERNANCE.md](../PRODUCTION_GOVERNANCE.md)  
**Platform snapshot:** [PLATFORM_STATE.md](../PLATFORM_STATE.md)

Проект перешёл из **Formal Runtime Governance + Stabilization** в фазу **Operational Maturity**: расширенный operational control при сохранении frozen runtime и stabilization execution.

> Главный актив проекта — **operational governance discipline**, не только runtime. Её необходимо сохранять.

---

## Текущее состояние

Production **operational**. Runtime Foundation стабилен = **infrastructure foundation** (`3de56f8c` FROZEN).

Подтверждено operational: Flask/Gunicorn, Redis, Google integrations, booking slots, Socket.IO, Node proxy, systemd, Nginx, SSL, health endpoints, Google Sheets validation, Telegram notifications.

---

## Governance entrypoint

| Документ | Роль |
|----------|------|
| [PRODUCTION_GOVERNANCE.md](../PRODUCTION_GOVERNANCE.md) | Governance index |
| [PLATFORM_STATE.md](../PLATFORM_STATE.md) | **Canonical platform snapshot** |
| [STABILIZATION_QA_PHASE.md](STABILIZATION_QA_PHASE.md) | Operational scope / P1 / P2 |
| [RUNTIME_GOVERNANCE.md](RUNTIME_GOVERNANCE.md) | Runtime freeze + change control |
| [OPERATIONAL_MATURITY_PHASE.md](OPERATIONAL_MATURITY_PHASE.md) | Current phase (этот файл) |

Все production-решения синхронизируются **только** через эти документы.

---

## Formal runtime governance

| Правило | Значение |
|---------|----------|
| Frozen baseline | `3de56f8c` |
| Change control | issue · rollback · smoke · justification · **explicit approval** |
| Без всех пяти | **CHANGE REJECTED** |

---

## Four-layer model

| Layer | Status |
|-------|--------|
| Runtime Foundation | **FROZEN** |
| Frontend UX | ACTIVE (`48dc9c64`) |
| Content Pipeline | ACTIVE |
| Ops / Observability | ACTIVE |

Изменения между слоями — **минимально связаны**.

---

## Release discipline

**ОДИН DEPLOY = ОДИН RELEASE TYPE.**

| Type | Scope |
|------|-------|
| `runtime` | backend / infrastructure |
| `frontend` | CSS / templates / UX |
| `content` | parser / blog / Sheets |
| `ops` | monitoring / security / deploy |

Runtime + frontend mixed deploy **запрещён** без approval. См. [RELEASE_TYPES.md](RELEASE_TYPES.md).

---

## Deploy flow

```
Изменение → release type → RELEASE_GATE_CHECKLIST → production_smoke.sh
         → Mobile QA (frontend) → deploy → post-deploy smoke → rollback при FAIL
```

---

## Operational maturity артефакты

| # | Артефакт | Путь | Статус |
|---|----------|------|--------|
| 1 | Ownership matrix | [OWNERSHIP_MATRIX.md](../ops/OWNERSHIP_MATRIX.md) | создан → **заполнить имена** |
| 2 | Release notes registry | [releases/](../releases/) | активен |
| 3 | Environment policy | [ENVIRONMENT_POLICY.md](ENVIRONMENT_POLICY.md) | активен |
| 4 | Severity escalation | [SEVERITY_ESCALATION_MATRIX.md](../ops/SEVERITY_ESCALATION_MATRIX.md) | активен |
| 5 | Production audit log | [PRODUCTION_AUDIT_LOG.md](../ops/PRODUCTION_AUDIT_LOG.md) | активен |

---

## Обязательные post-deploy действия

**Без этого deploy считается governance-incomplete / незавершённым.**

| # | Действие | Артефакт |
|---|----------|----------|
| 1 | Запись deploy | [PRODUCTION_AUDIT_LOG.md](../ops/PRODUCTION_AUDIT_LOG.md) |
| 2 | Release note (type, commit, rollback ref) | [releases/](../releases/) |
| 3 | Smoke PASS | `scripts/production_smoke.sh` |
| 4 | Mobile QA PASS | [MOBILE_QA_MATRIX.md](../qa/MOBILE_QA_MATRIX.md) (только `frontend`) |

---

## Stabilization execution (продолжается в этой фазе)

### P1 — execute now

| Track | Артефакт |
|-------|----------|
| Mobile QA matrix | [MOBILE_QA_MATRIX.md](../qa/MOBILE_QA_MATRIX.md) |
| Blog visibility | [BLOG_CONTENT_VISIBILITY.md](BLOG_CONTENT_VISIBILITY.md) |
| Checklist visuals | design assets (не менять rendering/routing) |
| Reviews / static | nginx `/static/`, avatars, lazy/eager |

### P2 — hardening & maturity

| Track | Items |
|-------|-------|
| Hardening | fail2ban, UFW, logrotate, backup, Redis persistence, gzip, certbot, rate limit, alerts |
| Observability | smoke, healthcheck, rollback validation |
| CI/CD | tagging, reproducibility, release notes, secrets hygiene |

**До stabilization exit:** никаких runtime refactor.

---

## Следующие практические шаги

1. Заполнить реальные ownership names в [OWNERSHIP_MATRIX.md](../ops/OWNERSHIP_MATRIX.md)  
2. Начать Mobile QA matrix (A1, A2, I1, T1)  
3. Завершить P2 hardening на сервере ([TIMEWEB_PRODUCTION_RUNBOOK.md](TIMEWEB_PRODUCTION_RUNBOOK.md))  
4. Вести audit log после каждого deploy  
5. Соблюдать release discipline (один type на deploy)  

---

## Exit criteria (stabilization + maturity)

- [ ] Ownership matrix — имена назначены  
- [ ] Mobile QA — все платформы PASS  
- [ ] P2 hardening завершён  
- [ ] Blog visible content (content layer)  
- [ ] Audit log ведётся на каждом deploy  
- [ ] Demo / investor ready  

**После exit:** SEO, parser scaling, sponsor platform, AI orchestration, tourism ecosystem, advanced analytics, growth automation.

---

## Baselines (reference)

| Layer | Commit | Status |
|-------|--------|--------|
| Runtime Foundation | `3de56f8c` | FROZEN |
| Frontend/docs | `48dc9c64` | ACTIVE |
| Operational maturity pack | `1858292d` | ACTIVE |
