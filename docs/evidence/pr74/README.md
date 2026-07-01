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

## Post-QA cleanup

**Status:** **COMPLETED**  
**Date:** 2026-07-01  
**Executed:** 2026-07-02T00:43Z via `tools/social_qa_cleanup.py --execute`  
**Cleanup type:** Google Sheets cleanup (service account, read-write Social tabs only)  
**Backup sheet:** `QA_CLEANUP_2026-07-01` — 8 rows backed up before delete  
**Production incident:** NO  
**Server/deploy changes:** NO

```text
CLEANUP=PASS
Social_Applications data rows after cleanup: 0
Social_Sessions data rows after cleanup: 0
Social_Audit_Log data rows after cleanup: 0
```

Owner verify: `/admin/social/` — empty list expected (no real applications).

### Tabs touched

- `Social_Applications`
- `Social_Sessions`
- `Social_Audit_Log`

**Not touched:** Workouts, Client_Workouts, Clients, Calendar, booking tabs.

### Removed (both QA pairs)

| Tab | ID | Notes |
|-----|-----|-------|
| `Social_Applications` | `soc_app_41d546e3b5aa47ea` | PR74 Browser QA real assign |
| `Social_Sessions` | `soc_sess_800eaf177db24034` | linked session |
| `Social_Applications` | `soc_app_e7be01a15ded4365` | earlier QA/test row |
| `Social_Sessions` | `soc_sess_e41e448019644a73` | linked session |

### Audit rows removed

All `Social_Audit_Log` rows containing any of:

```text
soc_app_41d546e3b5aa47ea
soc_sess_800eaf177db24034
soc_app_e7be01a15ded4365
soc_sess_e41e448019644a73
```

### Second candidate decision

| Item | Action | Reason |
|------|--------|--------|
| `soc_app_e7be01a15ded4365` | **REMOVED** | QA/test: «Тест Тестов», `+1234567890`, `@MyW23`, `owner_phase_b` |
| `soc_sess_e41e448019644a73` | **REMOVED** | QA/test: coach «Test Coach», `adaptive_wake`, Павильон |

### Deletion order (bottom-up per tab)

1. Backup → `QA_CLEANUP_2026-07-01`
2. `Social_Applications`: row 3, then row 2
3. `Social_Sessions`: row 3, then row 2
4. `Social_Audit_Log`: find/delete by ID (`Ctrl+F`)

### Post-cleanup verify

- Open `/admin/social/` — QA rows should disappear
- Empty list is OK if no real applications remain

### Pre-cleanup screenshots

| File | Description |
|------|-------------|
| `screenshots/cleanup/01_social_applications_before.png` | 2 QA application rows |
| `screenshots/cleanup/02_social_sessions_before.png` | 2 QA session rows |
| `screenshots/cleanup/03_social_audit_log_before.png` | 4 audit rows |

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
