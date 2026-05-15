# Release: <type> — <title>

| Field | Value |
|-------|-------|
| Date | YYYY-MM-DD |
| Release type | runtime / frontend / content / ops |
| Commit | `<full-or-short-sha>` |
| Rollback commit | `<prev-sha>` |
| Deployer | |
| Smoke | PASS / FAIL |
| Mobile QA | PASS / N/A |

## Summary

<1–3 предложения: что изменилось и зачем>

## Scope (layer)

- [ ] Runtime Foundation
- [ ] Frontend UX
- [ ] Content Pipeline
- [ ] Ops / Observability

## Checks

- [ ] RELEASE_GATE_CHECKLIST
- [ ] production_smoke.sh post-deploy
- [ ] PRODUCTION_AUDIT_LOG updated

## Rollback

<команды или ссылка на POST_DEPLOY_ROLLBACK.md>

## Notes

<риски, follow-ups>
