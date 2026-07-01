# PR74 — Admin shell and navigation hardening — Production Deploy Evidence

**Status:** **ACCEPTED** — DEPLOYED / Browser QA PASS  
**Date:** 2026-06-30 (deploy) · 2026-07-01 (Browser QA closure)  
**Merge commit:** `ffc08afc` (`ffc08afcb20c557b0ed329db28bf49fabe265bae`)  
**Head commit:** `b710a087`  
**Previous HEAD:** `bef474a9`  

```text
BROWSER_QA=PASS
PR74=ACCEPTED
DEPLOY_SHA=ffc08afc
Production incident: NO
```

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

## Browser QA — shell / navigation (PASS)

| Check | Result |
|-------|--------|
| `/admin/` new admin shell | PASS |
| Sidebar + topbar | PASS |
| No public header/nav/footer | PASS |
| No floating chat in admin | PASS |
| Social list | PASS |
| Images page | PASS |
| Blog / Events / Users / Settings stubs | PASS |
| Dashboard looks like admin workspace | PASS |
| Public UI regression | NO |

## Browser QA — detail / assign (PASS, 2026-07-01)

| Check | Result |
|-------|--------|
| Social detail opens | PASS |
| Status / age / city / contact / parent visible | PASS |
| `health_notes` / `motivation_text` / `internal_notes` absent | PASS |
| `has_safety_info` only yes/no + «содержимое не показывается» | PASS |
| Assign form opens | PASS |
| Confirmation step (warning card) appears | PASS |
| Real assign gated by `confirm=yes` | PASS (code + Owner flow) |

### Screenshots

| File | Description |
|------|-------------|
| `screenshots/01_social_detail_safe_fields.png` | Detail card: safe fields only, no sensitive text |
| `screenshots/02_assign_confirmation_step.png` | Assign step 2: warning card before final confirm |

## Owner QA note — real assign performed

During final Browser QA, Owner completed a **real assign** (intentional end-to-end test):

| Item | Value |
|------|-------|
| `application_id` | `soc_app_41d546e3b5aa47ea` |
| `session_id` | `soc_sess_800eaf177db24034` |
| `status` after assign | `scheduled` |
| `session_date` / `time` / `location` | 2026-07-04 / 11:00 / Руза |
| Audit trail | `session_assigned`, `application_status_changed` (new → scheduled) |
| Telegram admin notification | sent («Social session scheduled») |

**Not a production incident** — documented as Owner QA test assignment in Sheets.

## Not changed

- Social assignment business logic (`manual_assign_social_session` contract)
- Google Sheets schema
- `.env`, feature flags
- Notifications v2 runtime
- Password reset flow

## Related

- PR70/PR71/PR73 evidence: `docs/evidence/pr70/`, `pr71/`, `pr73/`
- PR72 (docs): `ee934d43` — evidence + Notifications v2 prep
- Notifications v2 prep: `docs/integration/NOTIFICATIONS_V2_PREP.md`

## Rollback

Code: `git reset --hard bef474a9` + `systemctl restart mywave-site` (if needed).
