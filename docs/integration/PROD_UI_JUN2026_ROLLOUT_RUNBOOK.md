# Production UI rollout — release/prod-ui-jun2026

**Status:** PREPARED — **NOT EXECUTED**  
**Base:** `ae4b6272` (PR45 prod hotfix)  
**Target:** `797c7f5d` (`release/prod-ui-jun2026` tip)  
**Date:** 2026-06-18

## Scope

Included: brand logo, ticker 840s/v5, hero #34–#42, Social Mission UI, services order, PR28 blog URL hygiene, PR45 upload (in base), backfill runbook docs-only.

Excluded: Events PR #22–26, backfill execution, Sheet edits, Parser cron, TGbotAdmin.

## Flags (production `.env` — after GM execution approval)

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

Pre-check: `.env` Sheets tails per `SHEETS_ID_CANON.md`; run `PROD_SOCIAL_READINESS_ONESHOT.md` (Option A) or `prod_social_readiness_check.sh` after merge.

## Commands (after approval)

```bash
PROD_ROOT=/var/www/mywave
TS=$(date +%Y%m%d_%H%M%S)
GIT="git -c safe.directory=${PROD_ROOT}"

$GIT -C "$PROD_ROOT" rev-parse HEAD | tee "/var/backups/mywave/head.pre_ui_rollout_${TS}.txt"
sudo cp "$PROD_ROOT/.env" "/var/backups/mywave/.env.pre_ui_rollout_${TS}"

cd "$PROD_ROOT"
$GIT fetch origin release/prod-ui-jun2026
$GIT checkout main
$GIT merge --ff-only origin/release/prod-ui-jun2026
$GIT diff ae4b6272..HEAD --stat   # STOP if unexpected files

# Apply SOCIAL_* flags per GM (separate step)
sudo APP_ROOT="$PROD_ROOT" bash scripts/ensure_media_upload_dirs.sh
sudo systemctl restart mywave-site
```

## Rollback

```bash
PREV=$(cat /var/backups/mywave/head.pre_ui_rollout_<TS>.txt)
$GIT -C /var/www/mywave checkout "$PREV"
sudo cp /var/backups/mywave/.env.pre_ui_rollout_<TS> /var/www/mywave/.env
sudo systemctl restart mywave-site
```

## Smoke

`/health` 200 · hero/logo desktop+mobile · ticker scroll · `/social` · form submit · upload 201 · journal clean.
