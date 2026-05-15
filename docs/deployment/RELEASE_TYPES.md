# Release Types — MyWaveWake

**Фаза:** Production Stabilization + QA Discipline  
**Индекс:** [PRODUCTION_GOVERNANCE.md](../PRODUCTION_GOVERNANCE.md)

| Baseline | Commit | Статус |
|----------|--------|--------|
| Runtime Foundation | `3de56f8c` | FROZEN |
| Frontend/docs | `48dc9c64` | ACTIVE |
| QA/Ops governance | `0a2a0e1a` | ACTIVE |
| Production state/docs | `94fbc211` | ACTIVE |

## Правило: ОДИН DEPLOY = ОДИН RELEASE TYPE

Каждый production deploy классифицируется **ровно одним** типом. См. [RELEASE_GATE_CHECKLIST.md](RELEASE_GATE_CHECKLIST.md).

**Запрещено:** смешанный runtime + frontend (или runtime + ops) hotfix в одном deploy без отдельного issue, gate и approval.

---

## Типы релизов

| Type | Слой | Что меняется | Approval | Smoke | Mobile QA |
|------|------|--------------|----------|-------|-----------|
| **runtime** | 1. Runtime Foundation | Flask, Gunicorn, Redis, health, booking, Google init | issue + rollback + justification | обязательно | N/A |
| **frontend** | 2. Frontend UX | CSS, templates, static images, JS (без API contract) | не нужен для CSS-only | обязательно | обязательно |
| **content** | 3. Content Pipeline | Sheets statuses, parser, slug, cache invalidate | не для code routing | `/blog` 200 | N/A |
| **ops** | 4. Ops/Observability | nginx, fail2ban, cron, backup, monitoring scripts | runbook review | обязательно | N/A |

---

## Tagging convention (рекомендация)

```
runtime/v1.0.0-3de56f8c    # только при approved runtime change
frontend/v1.1.0-<shortsha>
content/2026-05-15
ops/2026-05-15-hardening
```

Git tag создаётся **после** успешного post-deploy smoke.

---

## Rollback по типу

| Type | Rollback target |
|------|-----------------|
| runtime | `3de56f8c` + `systemctl restart mywave-site` |
| frontend | предыдущий frontend commit |
| content | откат статусов в Sheets / parser resync |
| ops | revert nginx/cron config + reload |

---

## Release notes (минимум)

```markdown
## Release <type>/<id>
- Date:
- Commit:
- Layer:
- Rollback commit:
- Smoke: PASS/FAIL
- Mobile QA: PASS/N/A
- Notes:
```

---

## Запрещённые комбинации

- **runtime + frontend** в одном deploy без отдельного gate и issue  
- **runtime** без frozen-runtime approval  
- deploy без `production_smoke.sh` post-check  

---

## Связанные документы

- [STABILIZATION_QA_PHASE.md](STABILIZATION_QA_PHASE.md)  
- [RELEASE_GATE_CHECKLIST.md](RELEASE_GATE_CHECKLIST.md)  
- [POST_DEPLOY_ROLLBACK.md](POST_DEPLOY_ROLLBACK.md)
