# Ownership Matrix — MyWaveWake

**Production:** https://mywavewake.ru  
**Governance:** [PRODUCTION_GOVERNANCE.md](../PRODUCTION_GOVERNANCE.md) · [PLATFORM_STATE.md](../PLATFORM_STATE.md)  
**Status:** integrated in governance model (`0d07eee7` / `544f518a`) — часть **production governance**  
**Updated:** 2026-05-15  
**Release:** [2026-05-15-operational-pack-ownership-qa.md](../releases/2026-05-15-operational-pack-ownership-qa.md)

Фиксирует **ownership зон production**. Критические роли закреплены за Owner / MyWave с эскалацией к project owner до назначения внешней команды.

---

## Production zones

| Zone | Primary owner | Backup | Scope | Decision rule |
|------|---------------|--------|-------|---------------|
| **Runtime** | Ярослав / MyWave (runtime owner) | backend lead | Flask, Gunicorn, SQLAlchemy, Redis, Socket.IO, health, booking API | issue + rollback + smoke + justification + explicit approval |
| **Frontend UX** | frontend lead (MyWave) | Ярослав / Owner | CSS, templates, static UX, Mobile QA sign-off | runtime untouched; QA + smoke PASS |
| **Blog pipeline** | parser / content (MyWave) | Ярослав / Owner | Sheets statuses, parser sync, slug, visibility | content only; no routing/runtime |
| **Infra** | ops (MyWave) | Ярослав / Owner | Nginx, SSL, systemd, Timeweb, UFW, fail2ban | ops release; smoke required |
| **Smoke** | release manager (Ярослав / MyWave) | ops | `production_smoke.sh`, release gate | deploy incomplete until smoke PASS |
| **Rollback** | runtime owner (Ярослав / MyWave) | release manager | rollback к `3de56f8c` | SEV-1 → immediate rollback |
| **DNS / SSL** | infra owner (MyWave ops) | ops | certbot, domains, redirects | audit log обязателен |

---

## Критические роли (зафиксированы)

| Роль | Назначение | Имя / контакт | Статус |
|------|------------|---------------|--------|
| **runtime owner** | freeze scope, runtime approval, SEV-1 rollback | Ярослав / MyWave + backend lead | active |
| **release manager** | gate, smoke, deploy completeness | Ярослав / MyWave | active (temporary) |
| **infra owner** | Nginx, SSL, Timeweb, hardening | MyWave ops — уточнить имя | temporary |
| **rollback owner** | = runtime owner | Ярослав / MyWave | active |

> **Правило:** release manager не должен быть единственным исполнителем runtime change без второго approver (Owner).

---

## Decision rights

| Действие | Approver | Evidence required |
|----------|----------|-------------------|
| Runtime change (freeze scope) | runtime owner + explicit Owner approval | issue, rollback, smoke, justification |
| Production deploy | release manager (gate PASS) | release note, audit log, `production_smoke.sh` |
| Frontend UX deploy | frontend lead + Mobile QA PASS | [MOBILE_QA_MATRIX.md](../qa/MOBILE_QA_MATRIX.md), screenshots |
| Content visibility | parser / content owner | Sheets rows/statuses |
| Ops / hardening | infra owner | runbook, rollback cmd, smoke |
| SEV-1 rollback | runtime owner immediately | incident note + post-rollback smoke |

---

## Escalation

| Ситуация | Эскалация | Target |
|----------|-----------|--------|
| SEV-1 / SEV-2 | runtime owner → project owner | immediate / < 30 min |
| Smoke FAIL | release manager → zone owner | stop / rollback |
| Mixed runtime+UX | **REJECT** → split | before work |
| Secret in diff | release manager → project owner | stop deploy |
| Mobile QA FAIL | frontend lead → release manager | frontend fix only |

См. [SEVERITY_ESCALATION_MATRIX.md](SEVERITY_ESCALATION_MATRIX.md)

---

## Имена — реестр ролей

| Role | Имя / контакт | Дата | Статус |
|------|---------------|------|--------|
| project owner | Ярослав / MyWave | 2026-05-15 | active |
| runtime owner | Ярослав / MyWave | 2026-05-15 | active |
| release manager | Ярослав / MyWave | 2026-05-15 | temporary |
| backend lead | MyWave — назначить имя | 2026-05-15 | temporary |
| frontend lead | MyWave — назначить имя | 2026-05-15 | temporary |
| parser / content | MyWave — назначить имя | 2026-05-15 | temporary |
| ops / infra owner | MyWave — назначить имя | 2026-05-15 | temporary |

---

## Owner follow-up

- [ ] Заменить temporary roles на реальные имена команды  
- [ ] Добавить Telegram / GitHub contacts  
- [ ] Назначить backup для Runtime и Infra  
- [ ] Подтвердить separation: release manager ≠ solo runtime change executor  

**Draft source:** [OWNERSHIP_MATRIX_FILLED_DRAFT.md](OWNERSHIP_MATRIX_FILLED_DRAFT.md)
