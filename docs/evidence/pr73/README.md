# PR73 — UserMixin hotfix — Production Deploy Evidence

**Status:** DEPLOYED / PASS  
**Date:** 2026-06-30  
**Merge commit:** `bef474a9` (`bef474a994e09546af58a3c427eb7c7464a4bb11`)  
**Previous HEAD:** `83daf51f`  
**Production incident:** NO

## Problem closed

```text
POST /login → 500 AttributeError: 'User' object has no attribute 'is_active'   (before PR73)
POST /login → 200/302 (authenticated)                                       (after PR73)
```

## Root cause

`User` model did not inherit `UserMixin` from Flask-Login. After successful password check, `login_user()` failed on `is_active`.

## Fix

- `class User(UserMixin, db.Model)` in `app/database/models.py`
- `tests/unit/test_auth_user_flask_login.py`

## Deploy summary (Owner)

| Check | Result |
|-------|--------|
| Code reset | `bef474a9` |
| Import as `www-data` | PASS |
| `mywave-site` | active |
| `health/live`, `health/ready` | ok |
| `GET /login` | **200** |
| `POST /login` (admin user) | **PASS** |
| `/admin/social/` (no auth) | **302** → login |
| `prod_pr56_smoke.sh` | PASS |
| `.env` / feature flags | unchanged |
| DB migrations | none |

## Auth DB bootstrap (prerequisite, Owner)

| Check | Result |
|-------|--------|
| Active DB | `sqlite:////var/www/mywave/instance/mywave.db` |
| `user` table | created |
| Admin user | `y.valeev@gmail.com`, `is_admin=True` |
| Backup | `mywave.db.pre_owner_admin_retry_*` |

## Browser QA (post-PR73)

| Check | Result |
|-------|--------|
| Login | PASS |
| `/admin/social/` list | PASS |
| `/admin/images` | PASS |
| Admin shell polish | deferred to **PR74** |

## Not changed

- PR70 Social admin logic
- API `/api/social/sessions/assign`
- `.env`, feature flags, Telegram, Sheets schema

## Related

- PR74: admin shell / navigation — see `docs/evidence/pr74/README.md`
- Auth bootstrap runbook: `docs/integration/AUTH_DB_BOOTSTRAP_READONLY.md`

## Rollback

Code: `git reset --hard 83daf51f` + `systemctl restart mywave-site` (if needed).
