# PR #45 — Production-only hotfix runbook (upload endpoint)

**Status:** PREPARED — **do not execute** until GM/Owner approval  
**Date:** 2026-06-18  
**Scope:** `POST /api/blog/media/upload` HTTP 500 fix only  
**Not in scope:** full `develop` deploy, backfill, Sheet edits, UI changes

---

## Package summary

| Field | Value |
|-------|--------|
| **Hotfix branch** | `hotfix/pr45-media-upload-prod` |
| **Base commit** | `origin/main` @ `df26212d` (`fix(booking): break Step 5 circular import…`) |
| **Cherry-picked** | `2ac9feef` → hotfix commit `c3c26b73` (same patch, backfill runbook excluded) |
| **Staging proof** | develop `6fcf7884` — upload smoke **PASS** (18 Jun 2026) |
| **Production** | **NOT EXECUTED** |

---

## Files included (5)

| File | Change |
|------|--------|
| `app/routes/api.py` | Safe file size, 507 JSON on mkdir/save errors, safe logging, localhost skip in `public_url` |
| `scripts/ensure_media_upload_dirs.sh` | Create `static/uploads/review_media` + permissions |
| `automation/production/prod_media_upload_diagnose.sh` | Read-only prod diagnostics |
| `tests/integration/test_media_upload_api.py` | Regression tests (item-112 JPG, 400/401/507, etc.) |
| `docs/integrations/MEDIA_UPLOAD_SETUP.md` | Ops note for upload dirs |

**Diff vs `main`:** 5 files, +329 / −17 lines

---

## Files explicitly excluded

| Excluded | Reason |
|----------|--------|
| `docs/integration/BLOG_MEDIA_BACKFILL_RUNBOOK.md` | Not on `main`; backfill blocked |
| Social Mission UI/API (`templates/`, `social-mission.css`, routes) | Unrelated to upload |
| Hero/logo/header/footer CSS | Unrelated |
| Ticker JS/CSS | Unrelated |
| `tests/unit/test_blog_media_regression.py` | Not on `main` (develop-only) |
| Any Sheet / Parser / TGbotAdmin changes | Out of scope |
| `.env` changes | No config change required for hotfix |

---

## Diff summary (`app/routes/api.py`)

1. `_media_upload_file_size()` — non-seekable WSGI streams  
2. `os.makedirs` / `media_file.save` wrapped in `try/except OSError` → **507 JSON**  
3. Structured logs: `media_upload_mkdir_failed`, `media_upload_save_failed` (`saved_name`, not `filename`)  
4. `_build_public_media_url()` — skip `localhost` / `127.0.0.1` in `SITE_BASE_URL`; relative fallback  

No changes to auth, cache invalidate, booking, or other routes.

---

## Tests (run before merge to `main`)

```bash
cd /path/to/repo
python -m pytest tests/integration/test_media_upload_api.py -q
```

**Expected:** 15 passed (verified on hotfix branch vs `main` base).

---

## Pre-execution checklist (Owner)

- [ ] GM written approval for **this runbook only**
- [ ] Backup: `git rev-parse HEAD` saved to `/var/backups/mywave/head.pre_pr45_<TS>.txt`
- [ ] Optional: `.env` backup (`chmod 600`)
- [ ] Confirm prod HEAD = `df26212d` (or document current before hotfix)
- [ ] `MEDIA_UPLOAD_TOKEN` present in prod `.env` (do not log value)

---

## Prod commands (execute only after approval)

```bash
PROD_ROOT=/var/www/mywave
TS=$(date +%Y%m%d_%H%M%S)

# 0) Record rollback point
sudo -u www-data git -C "$PROD_ROOT" rev-parse HEAD | tee "/var/backups/mywave/head.pre_pr45_${TS}.txt"

# 1) Fetch hotfix branch (or merge PR to main first)
cd "$PROD_ROOT"
sudo -u www-data git fetch origin hotfix/pr45-media-upload-prod

# Option A — merge hotfix branch into prod checkout on main
sudo -u www-data git checkout main
sudo -u www-data git merge --ff-only origin/hotfix/pr45-media-upload-prod

# Option B — cherry-pick single commit onto current prod main
# sudo -u www-data git cherry-pick c3c26b73

# 2) Verify only expected files changed
git diff df26212d..HEAD --stat

# 3) Upload directories (filesystem, not in Git)
sudo APP_ROOT="$PROD_ROOT" bash scripts/ensure_media_upload_dirs.sh

# 4) Restart Flask only
sudo systemctl restart mywave-site
sudo systemctl is-active mywave-site
```

**Services to restart:** `mywave-site` only  
**Do not restart:** `mywave-staging`, `mywave-node`, `mywave-telegram-bot` (unless separately approved)

---

## Smoke commands (prod, after restart)

```bash
PROD_ROOT=/var/www/mywave
PROD_URL=https://mywavewake.ru

# Read-only diagnose first
sudo bash "$PROD_ROOT/automation/production/prod_media_upload_diagnose.sh"

# Auth/route check (no file)
set -a && source "$PROD_ROOT/.env" && set +a
curl -sS -o /dev/null -w 'no_file HTTP=%{http_code}\n' \
  -X POST "$PROD_URL/api/blog/media/upload" \
  -H "Authorization: Bearer ${MEDIA_UPLOAD_TOKEN}"
# Expected: HTTP 400

# Real file upload
printf '\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9' \
  > /tmp/prod-upload-smoke.jpg
curl -sS -w "\nHTTP_CODE=%{http_code}\n" \
  -X POST "$PROD_URL/api/blog/media/upload" \
  -H "Authorization: Bearer ${MEDIA_UPLOAD_TOKEN}" \
  -F "file=@/tmp/prod-upload-smoke.jpg;type=image/jpeg"
# Expected: HTTP 201, JSON ok=true, public_url without localhost

ls -la "$PROD_ROOT/static/uploads/review_media/"

sudo journalctl -u mywave-site --since "10 min ago" --no-pager \
  | grep -iE 'media_upload|Unhandled|500|507' || echo "no upload errors"
```

### Expected HTTP codes

| Request | Code | Body |
|---------|------|------|
| No `file`, valid token | **400** | `{"error":"file is required"}` |
| Invalid token | **401** | `{"error":"unauthorized"}` |
| Valid JPG upload | **201** | `ok`, `public_url`, `filename`, `bytes` |
| Storage not writable (before ensure_dirs) | **507** | `upload storage unavailable` or `upload write failed` |
| Cache invalidate (unchanged) | **200** | (existing behaviour) |

---

## Rollback commands

```bash
PROD_ROOT=/var/www/mywave
PREV=$(cat /var/backups/mywave/head.pre_pr45_<TS>.txt)

cd "$PROD_ROOT"
sudo -u www-data git checkout "$PREV"
sudo systemctl restart mywave-site
sudo systemctl is-active mywave-site
curl -fsS https://mywavewake.ru/health
```

Uploaded files under `static/uploads/review_media/` **need not be deleted** on rollback.

---

## Production risk

| Risk | Level | Mitigation |
|------|-------|------------|
| Code change limited to upload handler | **Low** | 5 files only; 15 tests |
| `mywave-site` restart (~seconds downtime) | **Low** | Off-peak window; health check after |
| Wrong branch / full develop pull | **High** | Use `hotfix/pr45-media-upload-prod` only; verify `git diff --stat` |
| Filesystem permissions | **Medium** | `ensure_media_upload_dirs.sh` before smoke |
| Backfill accidentally triggered | **N/A** | No Sheet/Parser changes in package |

**Overall:** Low risk **if** hotfix branch is used and diff verified before restart.

---

## Guardrails (unchanged)

Do **not** without separate GM approval:

- Full `git pull origin develop` on prod  
- Blog media backfill / Sheet writeback  
- Parser cron / TGbotAdmin changes  
- Mass media upload batch  

---

## GM sign-off block (fill after execution)

```text
Execution date:
Prod HEAD before:
Prod HEAD after:
ensure_dirs: PASS/FAIL
upload smoke 201: PASS/FAIL
journal 500: none/FOUND
Rollback needed: yes/no
Approved by:
```
