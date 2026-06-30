# PR71 — Auth login template hotfix — Production Deploy Evidence

**Status:** DEPLOYED / PASS  
**Date:** 2026-06-29  
**Merge commit:** `83daf51f` (`83daf51fc70710f10286fd8aabd83555375c1408`)  
**Hotfix commit:** `29cde287`  
**Previous HEAD:** `de37a19e`  
**Production incident:** NO

## Problem closed

```text
GET /admin/social/ → 302 to /login
GET /login → 500 TemplateNotFound: auth/login.html   (before PR71)
GET /login → 200                                     (after PR71 deploy)
```

## Deploy summary (Owner, 2026-06-29)

| Check | Result |
|-------|--------|
| Code reset | `83daf51f` |
| Import as `www-data` | PASS |
| `mywave-site` | active |
| `health/live`, `health/ready` | ok |
| `GET /login` (local) | **200** |
| `GET /login` (public via nginx) | **200** |
| `/admin/social/` (no auth) | **302** → `/login?next=...` |
| `prod_pr56_smoke.sh --phase-b` | PASS |
| `.env` / feature flags | unchanged |
| `git_status` | `?? static/downloads/` only |

## Scope

- `templates/auth/login.html`
- `templates/auth/register.html`
- `tests/unit/test_auth_login_page.py`
- `docs/evidence/pr70/README.md` (diagnostics update)

## Not changed

- PR70 `/admin/social` logic
- API `/api/social/sessions/assign`
- `.env`, feature flags, Telegram, Sheets integration code

## Related

- PR70 Browser QA: **IN PROGRESS** — external access restored (VPN off); see `docs/evidence/pr70/README.md`
- Word «автоматически»: not present in login/register/evidence UI text

## Management decision (2026-06-29)

Notifications v2 preparation **allowed** in separate branch/PR. Constraints: no prod deploy, no merge without Owner review, no `.env`/flags/TGbotAdmin, no PR70/PR71 scope changes.

## Rollback

Code: `git reset --hard de37a19e` + `systemctl restart mywave-site` (if needed).
