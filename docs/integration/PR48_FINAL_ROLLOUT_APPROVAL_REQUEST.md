# PR #48 — Final rollout approval request (GM)

**Date:** 2026-06-19 (canonical sync)  
**PR:** https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/48  
**Status:** **REQUEST ONLY** — execution **NOT STARTED** until GM/Owner explicit approval  
**Preconditions:** Hero PASS · Social remediation A+B PASS

**Canonical source:** `git rev-parse origin/release/prod-ui-jun2026` after fetch — must match block below.

---

## Preconditions closed

| Blocker | Status | Evidence |
|---------|--------|----------|
| Hero visual | **CLOSED / PASS** | Owner sign-off + staging screenshots |
| Social readiness | **CLOSED / PASS** | `.env` dedupe + `Social_Applications` tab + rerun PASS |
| `.env` backup (remediation) | done | `/var/backups/mywave/.env.pre_social_remediation_20260619_130803` |

---

## § Final rollout block (canonical)

**Rule:** target = `git rev-parse origin/release/prod-ui-jun2026` after `git fetch`.  
**Site frozen verification:** 2026-06-19 (MSK), base `ae4b6272`.

```text
PR #48 target HEAD:           3d81ddbd (full: 3d81ddbdd78d485921fae55f8999f66cf9d06a7a)
origin/main current HEAD:     0274a54e (PR45 hotfix + deploy.yml safety)
production current HEAD:      ae4b6272 (PR45 hotfix; unchanged since hotfix)
diff stat:                    102 files, +124661 / −95  (ae4b6272..3d81ddbd)
diff name-only count:         102
Events leakage check:         PASS
DB migration check:           PASS (no migrations/)
Large static/binary paths:    43 under static/images/logotip_MyWave/MyWave_logo_package_brand_turquoise/
Execution status:             NOT STARTED
```

Docs-only commits after `3d81ddbd` may advance branch tip without changing the 102-file rollout payload.

---

## Verification output (Site, 2026-06-19)

```bash
git fetch origin release/prod-ui-jun2026 main
git rev-parse origin/release/prod-ui-jun2026
# 3d81ddbdd78d485921fae55f8999f66cf9d06a7a

git rev-parse origin/main
# 0274a54e243e32e836cf34800ac4a9c1a47fcbdd

git diff --stat ae4b6272..origin/release/prod-ui-jun2026
# 102 files changed, 124661 insertions(+), 95 deletions(-)

git diff --name-only ae4b6272..origin/release/prod-ui-jun2026 | wc -l
# 102

git diff --name-only ae4b6272..origin/release/prod-ui-jun2026 \
  | grep -Ei 'events|classifier|events_features' || echo PASS
# PASS

git diff --name-only ae4b6272..origin/release/prod-ui-jun2026 -- migrations/ || echo PASS
# PASS
```

---

## Diff manifest summary (102 files)

**App:** `app/__init__.py`, `app/config/social_features.py`, `app/routes/{api,brand,services,social}.py`, `app/services/{blog/*,brand/*,competitions/*,social_*}.py`, `config.py`, `configs/services.yaml`, `env.example`

**Docs:** `BLOG_MEDIA_BACKFILL_RUNBOOK.md` (docs-only), `PR48_FINAL_EVIDENCE_PACKAGE.md`, `PR48_FINAL_ROLLOUT_APPROVAL_REQUEST.md`, `PR48_SOCIAL_REMEDIATION_RUNBOOK.md`, `PROD_*`, `SHEETS_ID_CANON.md`, `SOCIAL_*`

**Scripts:** `scripts/prod_social_readiness_oneshot.py`, `scripts/prod_create_social_applications_tab.py`, `automation/production/prod_social_readiness_check.sh`

**Static/templates/tests:** branding CSS, social-mission, ticker, logo package (43 binary paths), templates, unit tests (social, hero, ticker, upload regression)

**Excluded from rollout intent:** Events PR #22–26, backfill execution, Parser cron, TGbotAdmin

---

## `.env` flags to apply (after code deploy, before restart)

**Do not change** spreadsheet IDs (remediation PASS). **Add or set:**

```env
SOCIAL_MODULE_ENABLED=1
SOCIAL_WIDGET_ENABLED=1
SOCIAL_APPLICATIONS_ENABLED=1
SOCIAL_PUBLIC_STATS_ENABLED=0
SOCIAL_ADMIN_NOTIFICATIONS_ENABLED=0

EVENTS_CLASSIFIER_ENABLED=0
EVENTS_API_ENABLED=0
EVENTS_PUBLIC_UI_ENABLED=0
```

Pre-restart verify:

```bash
grep -cE '^SPREADSHEET_ID=' /var/www/mywave/.env   # must be 1
PROD_ROOT=/var/www/mywave /var/www/mywave/venv/bin/python scripts/prod_social_readiness_oneshot.py
```

---

## Execution plan (after GM approval)

### Phase 0 — GitHub

1. Merge **PR #48** (`release/prod-ui-jun2026` @ `e68f46b0` → `main`).
2. Confirm `origin/main` matches merged tip.
3. Deploy workflow: `workflow_dispatch` only, `confirm=DEPLOY` (PR #47).

### Phase 1 — Production server

```bash
PROD_ROOT=/var/www/mywave
TS=$(date +%Y%m%d_%H%M%S)
GIT="git -c safe.directory=${PROD_ROOT}"

$GIT -C "$PROD_ROOT" rev-parse HEAD | tee "/var/backups/mywave/head.pre_ui_rollout_${TS}.txt"
sudo cp "$PROD_ROOT/.env" "/var/backups/mywave/.env.pre_ui_rollout_${TS}"

cd "$PROD_ROOT"
$GIT fetch origin main release/prod-ui-jun2026

# STOP-CONDITION checks
$GIT diff ae4b6272..origin/release/prod-ui-jun2026 --stat
$GIT diff --name-only ae4b6272..origin/release/prod-ui-jun2026 | wc -l   # expect 102
$GIT diff --name-only ae4b6272..origin/release/prod-ui-jun2026 \
  | grep -Ei 'events|classifier|events_features' && exit 1 || true

$GIT checkout main
$GIT merge --ff-only origin/main

# Apply SOCIAL_* flags in .env (manual)
sudo APP_ROOT="$PROD_ROOT" bash scripts/ensure_media_upload_dirs.sh
sudo systemctl restart mywave-site
```

### Phase 2 — Smoke (15 min)

```bash
curl -sf https://mywavewake.ru/health
curl -sI https://mywavewake.ru/social | head -1
sudo journalctl -u mywave-site --since "5 min ago" | grep -i traceback || echo "journal OK"
PROD_ROOT=/var/www/mywave bash automation/production/prod_social_readiness_check.sh
```

---

## Mandatory STOP-CONDITION

| # | Condition |
|---|-----------|
| 1 | `git merge --ff-only` fails |
| 2 | Events/migrations in diff vs `ae4b6272` |
| 3 | File count ≠ **102** |
| 4 | `SPREADSHEET_ID` count ≠ 1 |
| 5 | `Social_Applications_tab` ≠ YES |
| 6 | `/health` ≠ 200 |
| 7 | Traceback in journal |
| 8 | Upload (no file) → **500** |

---

## Services to restart

`mywave-site` only — `sudo systemctl restart mywave-site`

---

## Smoke checklist

1. `/health` → 200  
2. `/` desktop + mobile hero/logo  
3. Header/footer logo  
4. Ticker on home  
5. `/services` boat before gym  
6. `/social` → 200  
7. Upload without file → 400 (not 500)  
8. `prod_social_readiness_check.sh` → PASS  
9. journal 15 min clean  

---

## Rollback

```bash
PREV=$(cat /var/backups/mywave/head.pre_ui_rollout_<TS>.txt)
git -c safe.directory=/var/www/mywave -C /var/www/mywave checkout "$PREV"
sudo cp /var/backups/mywave/.env.pre_ui_rollout_<TS> /var/www/mywave/.env
sudo systemctl restart mywave-site
```

---

## Expected downtime

~30–60 s restart · ~1–3 min git (logo assets)

---

## Site request to GM

```text
Execution status: NOT STARTED
Awaiting: GM/Owner explicit "APPROVED: execute PR #48 prod rollout"
```
