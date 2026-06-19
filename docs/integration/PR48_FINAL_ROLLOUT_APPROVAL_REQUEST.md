# PR #48 — Final rollout approval request (GM)

**Date:** 2026-06-19  
**PR:** https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/48  
**Status:** **REQUEST ONLY** — execution **NOT STARTED** until GM/Owner explicit approval  
**Preconditions:** Hero PASS · Social remediation A+B PASS

---

## Preconditions closed

| Blocker | Status | Evidence |
|---------|--------|----------|
| Hero visual | **CLOSED / PASS** | Owner sign-off + staging screenshots |
| Social readiness | **CLOSED / PASS** | `.env` dedupe + `Social_Applications` tab + rerun PASS |
| `.env` backup (remediation) | done | `/var/backups/mywave/.env.pre_social_remediation_20260619_130803` |

---

## § Final rollout block

```text
PR #48 target HEAD:           de21ddbd (origin/release/prod-ui-jun2026)
origin/main current HEAD:     0274a54e (PR45 hotfix + deploy.yml safety)
production current HEAD:      ae4b6272 (PR45 hotfix; unchanged since hotfix)
Diff stat (ae4b6272..de21ddbd): 101 files, +124455 / −95
Diff name-only count:         101
Events leakage check:         PASS
DB migration check:           PASS (no migrations/)
Large static/binary paths:    43 under MyWave_logo_package_brand_turquoise/
Execution status:             NOT STARTED
```

Verify before execute:

```bash
git fetch origin release/prod-ui-jun2026 main
git rev-parse origin/release/prod-ui-jun2026   # expect de21ddbd
git diff --stat ae4b6272..origin/release/prod-ui-jun2026
git diff --name-only ae4b6272..origin/release/prod-ui-jun2026 | wc -l
git diff --name-only ae4b6272..origin/release/prod-ui-jun2026 \
  | grep -Ei 'events|classifier|events_features' || echo PASS
git diff --name-only ae4b6272..origin/release/prod-ui-jun2026 -- migrations/ || echo PASS
```

---

## Diff manifest summary (101 files)

**App:** `app/__init__.py`, `app/config/social_features.py`, `app/routes/{api,brand,services,social}.py`, `app/services/{blog/*,brand/*,competitions/*,social_*}.py`, `config.py`, `configs/services.yaml`, `env.example`

**Docs:** `BLOG_MEDIA_BACKFILL_RUNBOOK.md` (docs-only), `PR48_*`, `PROD_*`, `SHEETS_ID_CANON.md`, `SOCIAL_*`

**Scripts:** `scripts/prod_social_readiness_oneshot.py`, `scripts/prod_create_social_applications_tab.py`, `automation/production/prod_social_readiness_check.sh`

**Static/templates/tests:** branding CSS, social-mission, ticker, logo package (~43 binaries), templates, 55 unit tests scope

**Excluded from rollout intent:** Events PR #22–26, backfill execution, Parser cron, TGbotAdmin

---

## `.env` flags to apply (after code deploy, before restart)

**Do not change** spreadsheet IDs (remediation already PASS). **Add or set:**

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

Optional explicit (recommended if not already set):

```env
SOCIAL_SPREADSHEET_ID=<Admin, tail MOrCgic0>
SOCIAL_APPLICATIONS_SHEET_NAME=Social_Applications
```

Pre-restart verify tails:

```bash
grep -cE '^SPREADSHEET_ID=' /var/www/mywave/.env   # must be 1
PROD_ROOT=/var/www/mywave /var/www/mywave/venv/bin/python scripts/prod_social_readiness_oneshot.py
```

---

## Execution plan (after GM approval)

### Phase 0 — GitHub (Site or Owner)

1. Merge **PR #48** (`release/prod-ui-jun2026` → `main`) on GitHub.
2. Confirm `origin/main` = `de21ddbd` (or merge commit if non-FF).
3. **Do not** trigger deploy workflow unless using `workflow_dispatch` with `confirm=DEPLOY` (PR #47 safety).

### Phase 1 — Production server

```bash
PROD_ROOT=/var/www/mywave
TS=$(date +%Y%m%d_%H%M%S)
GIT="git -c safe.directory=${PROD_ROOT}"

# Backups
$GIT -C "$PROD_ROOT" rev-parse HEAD | tee "/var/backups/mywave/head.pre_ui_rollout_${TS}.txt"
sudo cp "$PROD_ROOT/.env" "/var/backups/mywave/.env.pre_ui_rollout_${TS}"

cd "$PROD_ROOT"
$GIT fetch origin main release/prod-ui-jun2026

# STOP-CONDITION: run mandatory checks (see below) BEFORE merge
$GIT diff ae4b6272..origin/release/prod-ui-jun2026 --stat
$GIT diff --name-only ae4b6272..origin/release/prod-ui-jun2026 \
  | grep -Ei 'events|classifier|events_features' && exit 1 || true

$GIT checkout main
$GIT merge --ff-only origin/main    # after PR #48 merged on GitHub

# STOP-CONDITION: unexpected diff vs release tip
$GIT rev-parse HEAD                 # must match origin/main post-merge
$GIT diff ae4b6272..HEAD --stat | head -5

# Apply SOCIAL_* / EVENTS_* flags in .env (manual edit — backup exists)
# nano /var/www/mywave/.env

sudo APP_ROOT="$PROD_ROOT" bash scripts/ensure_media_upload_dirs.sh
sudo systemctl restart mywave-site
```

### Phase 2 — Smoke (within 15 min)

```bash
curl -sf https://mywavewake.ru/health
curl -sI https://mywavewake.ru/ | head -1
curl -sI https://mywavewake.ru/social | head -1
curl -s -o /dev/null -w "%{http_code}" -X POST https://mywavewake.ru/api/blog/media/upload \
  -H "Authorization: Bearer $MEDIA_UPLOAD_TOKEN"   # expect 400 without file (not 500)
sudo journalctl -u mywave-site --since "5 min ago" | grep -i traceback || echo "journal OK"
PROD_ROOT=/var/www/mywave sudo bash automation/production/prod_social_readiness_check.sh
```

---

## Mandatory STOP-CONDITION (abort rollout)

**Stop immediately** if any of:

| # | Condition |
|---|-----------|
| 1 | `git merge --ff-only` fails |
| 2 | Diff vs `ae4b6272` includes `events_features`, `app/routes/events`, `templates/events`, or `migrations/` |
| 3 | File count ≠ **101** (re-verify with `wc -l`) |
| 4 | `SPREADSHEET_ID` count ≠ 1 after deploy (re-run readiness) |
| 5 | `Social_Applications_tab` ≠ YES |
| 6 | `GET /health` ≠ 200 within 60 s after restart |
| 7 | `journalctl -u mywave-site` shows Traceback on startup |
| 8 | `POST /api/blog/media/upload` (no file) returns **500** (regression PR45) |

On STOP: **do not** apply flags if not yet applied; if restart already done, execute rollback below.

---

## Services to restart

| Service | Action |
|---------|--------|
| `mywave-site` (gunicorn) | `sudo systemctl restart mywave-site` |

No nginx reload required unless config changed (not in this rollout).

---

## Smoke checklist

1. `/health` → 200  
2. `/` desktop — hero logo visible, header/footer turquoise logo  
3. `/` mobile ~400px — hero not clipped  
4. Competitions ticker scrolls on home  
5. `/services` — boat before gym  
6. `/social` → 200 (flags ON)  
7. Social form test submit → success row in `Social_Applications` (optional staging-style test on prod)  
8. `POST /api/blog/media/upload` without file → 400 (not 500)  
9. `prod_social_readiness_check.sh` → PASS  
10. journal 15 min — no Traceback  

---

## Rollback

```bash
TS=<same TS from rollout>
PREV=$(cat /var/backups/mywave/head.pre_ui_rollout_${TS}.txt)
GIT="git -c safe.directory=/var/www/mywave"
$GIT -C /var/www/mywave checkout "$PREV"
sudo cp "/var/backups/mywave/.env.pre_ui_rollout_${TS}" /var/www/mywave/.env
sudo systemctl restart mywave-site
curl -sf https://mywavewake.ru/health
```

Rollback removes Social UI/flags; **does not** remove `Social_Applications` tab (harmless).

---

## Expected downtime

| Item | Estimate |
|------|----------|
| `mywave-site` restart | **30–60 s** |
| git pull/merge on server | 1–3 min (large logo assets) |
| Total user-visible | ~1 min typical |

---

## Post-rollout (non-blocking)

- Hero logo/text nudge upward — Owner micro-tweak, separate issue  
- Blog backfill — **not in scope** (Owner decision: keep Place1Logo)  

---

## Site request to GM

**Request:** approve execution of PR #48 production UI rollout per commands above.

**Not approved until GM reply:** merge PR #48 · prod deploy · restart · Social flags ON.

```text
Execution status: NOT STARTED
Awaiting: GM/Owner explicit "APPROVED: execute PR #48 prod rollout"
```
