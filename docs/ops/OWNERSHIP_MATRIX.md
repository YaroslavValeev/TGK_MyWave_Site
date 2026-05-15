# Ownership Matrix — MyWaveWake

**Production:** https://mywavewake.ru  
**Governance:** [PRODUCTION_GOVERNANCE.md](../PRODUCTION_GOVERNANCE.md)

Фиксирует **ownership зон production**. Имена владельцев назначаются владельцем проекта; до назначения — роль (role).

---

## Production zones

| Zone | Owner (role) | Backup | Scope |
|------|--------------|--------|-------|
| **Runtime** | backend lead | — | Flask, Gunicorn, SQLAlchemy, Redis, Socket.IO, health, booking API |
| **Frontend UX** | frontend lead | — | CSS, templates, static UX, Mobile QA sign-off |
| **Blog pipeline** | parser / content | — | Sheets statuses, parser sync, slug, visibility |
| **Infra** | ops | — | Nginx, SSL, systemd, Timeweb, UFW, fail2ban |
| **Smoke** | release manager | ops | `production_smoke.sh`, release gate, post-deploy smoke |
| **Rollback** | runtime owner | release manager | rollback к `3de56f8c`, incident rollback |
| **DNS / SSL** | infra owner | ops | certbot, domains, redirects |

---

## Decision rights

| Действие | Approver |
|----------|----------|
| Runtime change (any freeze scope) | runtime owner + explicit approval |
| Production deploy | release manager (gate PASS) |
| Frontend UX deploy | frontend lead + Mobile QA PASS |
| Content visibility change | parser / content owner |
| Ops / hardening change | infra owner |
| SEV-1 rollback | runtime owner (немедленно, уведомить всех) |

---

## Escalation

| Ситуация | Эскалация |
|----------|-----------|
| SEV-1 / SEV-2 | runtime owner → project owner |
| Smoke FAIL после deploy | release manager → zone owner |
| Mixed runtime+UX deploy request | **REJECT** → split releases |

См. [SEVERITY_ESCALATION_MATRIX.md](SEVERITY_ESCALATION_MATRIX.md), [PRODUCTION_INCIDENT_POLICY.md](PRODUCTION_INCIDENT_POLICY.md).

---

## Имена (заполнить) — **следующий практический шаг фазы**

> Operational Maturity Phase не считается полностью активированной, пока таблица ниже не заполнена владельцем проекта.

| Role | Имя / контакт | Дата назначения |
|------|---------------|-----------------|
| backend lead | _TBD_ | |
| frontend lead | _TBD_ | |
| parser / content | _TBD_ | |
| ops | _TBD_ | |
| release manager | _TBD_ | |
| project owner | _TBD_ | |
