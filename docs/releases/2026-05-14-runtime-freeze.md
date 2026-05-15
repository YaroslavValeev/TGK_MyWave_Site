# Release: runtime — Runtime Foundation freeze

| Field | Value |
|-------|-------|
| Date | 2026-05-14 |
| Release type | runtime |
| Commit | `3de56f8c` |
| Rollback commit | `8ee0ca40` |
| Smoke | PASS |

## Summary

Зафиксирован **frozen runtime baseline** после P0 стабилизации: blog routing 200, health на canonical `db`, booking/slots operational. Runtime Foundation объявлен production infrastructure foundation.

## Scope

- Runtime Foundation: blog/health hotfixes (последний approved runtime change до freeze policy)

## Checks

- `/health` → 200
- `/blog` → 200
- `production_smoke.sh` equivalent checks PASS

## Rollback

`git checkout 8ee0ca40` — см. [POST_DEPLOY_ROLLBACK.md](../deployment/POST_DEPLOY_ROLLBACK.md)

## Notes

Все последующие runtime changes — только через 5-point change control. **Не откатывать** без SEV-1/SEV-2.
