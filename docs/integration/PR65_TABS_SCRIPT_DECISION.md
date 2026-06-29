# PR65 tabs script — decision (2026-06-29)

**Decision:** **optional backlog** — do not merge now.

| Item | Value |
|------|-------|
| Branch | `feature/pr56-sheets-tabs-script` |
| Commit | `75c44636` |
| Script | `scripts/prod_create_social_pr56_tabs.py` |
| Production | Tabs already created manually — **not blocking** |

## Rationale

- Production Social_Sessions / Social_Audit_Log headers verified at PR56 alignment.
- Script adds repeatability for **future** env bootstrap only.
- No production deploy or Owner commands required until a new environment is provisioned.

## When to merge

Merge PR65 before next staging/bootstrap where Social tabs must be created automatically.

```text
No production deploy without separate approval
No Owner server commands until bootstrap needed
```

## Admin UI MVP

Next active work: Admin UI for manual assign (`/admin/social`) — separate PR from PR65.
