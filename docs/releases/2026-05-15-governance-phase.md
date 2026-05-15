# Release: ops — Governance & operational maturity

| Field | Value |
|-------|-------|
| Date | 2026-05-15 |
| Release type | ops |
| Commits | `0a2a0e1a` … `15ee2680` (docs-only series) |
| Runtime commit | `3de56f8c` (unchanged) |
| Smoke | N/A (docs) / PASS on prod |

## Summary

Переход к **formal production-governed platform**: governance index, runtime governance, release gate, release types, incident policy, Mobile QA matrix, environment policy, ownership matrix, audit log, release notes registry.

## Scope

- Ops / Observability: documentation and process only
- Runtime: **FROZEN** at `3de56f8c`
- Frontend baseline: `48dc9c64`

## Key artifacts

| Document | Purpose |
|----------|---------|
| PRODUCTION_GOVERNANCE.md | Entrypoint |
| RUNTIME_GOVERNANCE.md | Freeze + CHANGE REJECTED |
| STABILIZATION_QA_PHASE.md | P1/P2 execution |
| RELEASE_GATE_CHECKLIST.md | Deploy gate |
| OWNERSHIP_MATRIX.md | Zone owners |
| ENVIRONMENT_POLICY.md | local/staging/prod |
| SEVERITY_ESCALATION_MATRIX.md | SEV actions |
| PRODUCTION_AUDIT_LOG.md | Deploy history |

## Checks

- No application code deploy required for docs
- `git pull` on server optional (docs only)

## Rollback

Revert docs commits; **не затрагивает** runtime.

## Notes

Главный актив проекта — **governance discipline**. Сохранять при всех P1/P2 работах.
