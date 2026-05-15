# Severity Escalation Matrix — MyWaveWake

**Production:** https://mywavewake.ru  
**Incidents:** [PRODUCTION_INCIDENT_POLICY.md](PRODUCTION_INCIDENT_POLICY.md)  
**Ownership:** [OWNERSHIP_MATRIX.md](OWNERSHIP_MATRIX.md)

---

## Матрица действий

| Severity | Описание | Немедленное действие | Deploy | Уведомление |
|----------|----------|----------------------|--------|-------------|
| **SEV-1** | Полный outage (502/503, Gunicorn down, DB down) | **immediate rollback** к `3de56f8c` | **STOP** all | Telegram + owner |
| **SEV-2** | Критический функционал (booking 5xx, health unhealthy core, chat down) | **deploy freeze** · rollback или approved hotfix | **FREEZE** | Telegram + runtime owner |
| **SEV-3** | Деградация (blog empty, health degraded optional, static 404) | monitored degradation · content/ops fix | разрешён non-runtime | backlog + zone owner |
| **SEV-4** | Косметика / UX | **backlog** | frontend release only | optional |

---

## Триггеры по severity

| Trigger | Severity |
|---------|----------|
| home/blog 502/503 | SEV-1 |
| `production_smoke.sh` FAIL (health, slots, home) | SEV-1 / SEV-2 |
| booking slots не 200 | SEV-2 |
| restart loop (Gunicorn/Node) | SEV-1 |
| массовые 5xx > 10/min post-deploy | SEV-1 |
| blog empty (routing OK) | SEV-3 |
| UX spacing / carousel | SEV-4 |

---

## Escalation timeline

| Severity | SLA первой реакции | Эскалация |
|----------|-------------------|-----------|
| SEV-1 | немедленно | project owner через 15 мин без mitigation |
| SEV-2 | < 30 мин | project owner через 1 ч |
| SEV-3 | < 4 ч | weekly review |
| SEV-4 | next sprint | Mobile QA matrix |

---

## Post-incident

1. Запись в [PRODUCTION_AUDIT_LOG.md](PRODUCTION_AUDIT_LOG.md)  
2. Release note (если deploy-related) в [releases/](../releases/)  
3. Обновление runbook при необходимости  
