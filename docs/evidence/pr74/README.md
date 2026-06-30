# PR74 — Admin shell and navigation hardening — Production Deploy Evidence

**Status:** DEPLOYED / **Browser QA MOSTLY PASS** (2 screenshots pending)  
**Date:** 2026-06-30  
**Merge commit:** `ffc08afc` (`ffc08afcb20c557b0ed329db28bf49fabe265bae`)  
**Head commit:** `b710a087`  
**Previous HEAD:** `bef474a9`  
**Production incident:** NO

## Scope deployed

- Standalone admin shell: sidebar + topbar (no public header/nav/footer/floating chat)
- Navigation fixed: Social, Images, stub pages for Blog / Events / Users / Settings
- Access control: `@login_required` + `@admin_required` on `/admin/*` and images routes
- Social list/detail/assign UI polish (business logic unchanged)
- Unit tests: `test_admin_navigation.py`, `test_admin_access_control.py` — **21 passed**

## Deploy summary (Owner)

| Check | Result |
|-------|--------|
| Code reset | `ffc08afc` |
| `HEAD` | `ffc08afc` |
| Import as `www-data` | PASS |
| `mywave-site` | active |
| `health/live`, `health/ready` | ok |
| `GET /login` | **200** |
| `/admin/` (no auth) | **302** |
| `/admin/social/` (no auth) | **302** |
| `/admin/images/` (no auth) | **302** |
| `prod_pr56_smoke.sh` | PASS |
| `.env` / DB migrations / TGbotAdmin / node / Notifications v2 | **not in scope** |

## Browser QA — confirmed (screenshots)

| Check | Result |
|-------|--------|
| `/admin/` new admin shell | PASS |
| Sidebar + topbar | PASS |
| No public header/nav/footer | PASS |
| No floating chat in admin | PASS |
| Social list | PASS |
| Images page | PASS |
| Blog stub (`/admin/blog`) | PASS |
| Events stub (`/admin/events`) | PASS |
| Users stub (`/admin/users`) | PASS |
| Settings stub (`/admin/settings`) | PASS |
| Dashboard looks like admin workspace | PASS |
| Public UI regression | NO |

## Browser QA — pending (2 screenshots)

Owner to capture **without submitting real assign**:

### 1. Social detail page

- [ ] Status / age / city / contact / parent visible
- [ ] `health_notes` / `motivation_text` / `internal_notes` **absent**
- [ ] `has_safety_info` shown only as yes/no (content not displayed)

Path: `/admin/social/` → «Открыть» on a `new` application.

### 2. Assign confirmation step

- [ ] Form fields filled
- [ ] Warning / confirmation card visible
- [ ] Button «Подтвердить назначение» visible
- [ ] **Real assign NOT submitted** (do not click final confirm)

Path: detail → «Назначить сессию» → fill fields → «Проверить и подтвердить».

## Code / unit-test confirmation (pre-screenshot)

| Check | Verified by |
|-------|-------------|
| Detail route exists | `admin_social.detail` |
| Sensitive fields hidden | `sanitize_application_for_admin()` + `test_detail_no_health_in_body` |
| Assign form opens | `assign.html` GET |
| Confirmation step before real assign | `confirm != "yes"` → `show_confirm=True` |
| `manual_assign_social_session()` gated | only when `confirm=yes` — `test_assign_requires_confirm` |

## Screenshots

Place final Browser QA captures under:

```text
docs/evidence/pr74/screenshots/
  01_social_detail_safe_fields.png
  02_assign_confirmation_step.png
```

## Closure criteria

When both screenshots are attached and checklist above is checked:

```text
BROWSER_QA=PASS
PR74=ACCEPTED
DEPLOY_SHA=ffc08afc
Production incident: NO
```

## Not changed

- Social assignment business logic (`manual_assign_social_session` contract)
- Google Sheets schema
- `.env`, feature flags
- Notifications v2 runtime
- Password reset flow

## Related

- PR70/PR71/PR73 evidence: `docs/evidence/pr70/`, `pr71/`, `pr73/`
- Notifications v2 prep: `docs/integration/NOTIFICATIONS_V2_PREP.md` (PR72)

## Rollback

Code: `git reset --hard bef474a9` + `systemctl restart mywave-site` (if needed).
