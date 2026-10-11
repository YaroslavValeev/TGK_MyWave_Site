# PR56 Production Rollout Runbook — Two-Phase Safe Deploy

**Status:** CLOSED / PASS (2026-06-28)  
**Production HEAD:** `3b70a038`  
**Evidence:** [docs/evidence/pr56/README.md](../evidence/pr56/README.md) · [release notes](../releases/2026-06-28-runtime-pr56-social-manual-assign.md)

**No further deploy actions required** — post-release QA observation only.

---

**Historical prerequisite:** hotfix scripts merged (`automation/production/prod_*`).  
**Historical prod baseline:** `c35d19cc` (PR55) → Phase A `716d81c0` → alignment `3b70a038`.

---

## Hard rules (production)

```text
NEVER:  chmod 600 /var/www/mywave/.env
NEVER:  git pull without explicit rollout approval
NEVER:  print secret values in console/chat
NEVER:  enable SOCIAL_BOOKING_ENABLED=true before Phase B approval
ALWAYS:  chown root:www-data .env && chmod 640 .env after .env edits
ALWAYS:  prod_env_readable_check.sh + prod_import_as_run_user.sh before restart
```

---

## `.env` permissions contract

| Item | Value |
|------|--------|
| Path | `/var/www/mywave/.env` |
| Owner | `root` |
| Group | `www-data` |
| Mode | `640` |
| Service user | `www-data` (`mywave-site.service`) |

Apply:

```bash
sudo bash /var/www/mywave/automation/production/prod_env_permissions_fix.sh
```

---

## Phase A — PR56 code in safe mode

**Goal:** deploy PR56 without enabling manual assign.

| Flag | Value |
|------|--------|
| `SOCIAL_MODULE_ENABLED` | `1` (if Social already on prod) |
| `SOCIAL_APPLICATIONS_ENABLED` | `1` |
| `SOCIAL_ADMIN_NOTIFICATIONS_ENABLED` | `1` (optional) |
| `SOCIAL_BOOKING_ENABLED` | **`false`** |
| `ADMIN_TOKEN` | may be SET (assign still blocked by flag) |

### Owner commands (Phase A)

```bash
cd /var/www/mywave

# 1. Backup
sudo MYWAVE_ROOT=/var/www/mywave bash deploy/scripts/backup_mywave.sh

# 2. Controlled code update (NOT blind git pull on prod until approved)
sudo -u www-data git fetch origin
sudo -u www-data git reset --hard 5216818c

# 3. Ensure booking flag OFF (does not print secrets)
grep -q '^SOCIAL_BOOKING_ENABLED=' .env \
  && sudo sed -i 's/^SOCIAL_BOOKING_ENABLED=.*/SOCIAL_BOOKING_ENABLED=false/' .env \
  || echo 'SOCIAL_BOOKING_ENABLED=false' | sudo tee -a .env >/dev/null

# 4. Fix .env permissions (mandatory after any .env touch)
sudo bash automation/production/prod_env_permissions_fix.sh

# 5. Pre-restart gates
sudo bash automation/production/prod_env_readable_check.sh
sudo bash automation/production/prod_import_as_run_user.sh

# 6. Restart + smoke
sudo systemctl restart mywave-site
sleep 3
sudo systemctl is-active mywave-site
curl -fsS http://127.0.0.1:5000/health/live
curl -fsS http://127.0.0.1:5000/health/ready
curl -fsS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5000/social

# 7. PR56 safe-mode smoke
sudo bash automation/production/prod_pr56_smoke.sh

# 8. Sheets headers probe (read-only)
sudo bash automation/production/prod_social_sessions_headers_check.sh
```

**Expected Phase A:**

```text
HEAD=5216818c
POST /api/social/sessions/assign → 503 (social_booking_disabled)
/social → 200
/api/calendar/slots/... → 200
```

---

## Phase B — Enable manual assign (separate approval)

**Prerequisite:** Phase A PASS + Sheets headers ready + `PR56 RE-ROLLOUT PHASE B APPROVED`.

### 1. Google Sheets headers (Owner manual if tabs missing)

**Social_Sessions** (row 1, 15 columns):

```text
session_id,application_id,created_at,updated_at,status,assigned_by,session_date,session_time,location,service_type,coach,notes,calendar_event_id,booking_id,source
```

**Social_Audit_Log** (row 1, 6 columns):

```text
event_id,timestamp,actor,action,application_id,payload_summary
```

Code **does not auto-create** these tabs — verify with:

```bash
sudo bash automation/production/prod_social_sessions_headers_check.sh
```

### Option A — write-safe script (recommended)

Same pattern as PR48 `Social_Applications` script:

```bash
# Dry-run (read-only probe + prints headers)
PROD_ROOT=/var/www/mywave /var/www/mywave/venv/bin/python scripts/prod_create_social_pr56_tabs.py

# Apply (creates missing tabs + row 1 only)
SOCIAL_TAB_CREATE_APPLY=1 PROD_ROOT=/var/www/mywave \
  /var/www/mywave/venv/bin/python scripts/prod_create_social_pr56_tabs.py

# Verify
bash automation/production/prod_social_sessions_headers_check.sh
```

**Scope:** Admin sheet only · header row 1 · no data rows · no booking/parser edits.

### Option B — Owner manual (Sheets UI)

Admin spreadsheet → Add sheet → paste row 1 only (no data rows). See header CSV above.

### 2. ADMIN_TOKEN setup (safe script)

```bash
sudo bash automation/production/prod_admin_token_setup.sh
```

Prints only: `ADMIN_TOKEN: SET`, `SOCIAL_BOOKING_ENABLED: false`, fingerprint prefix.

### 3. Enable manual assign

After Owner approval:

```bash
sudo sed -i 's/^SOCIAL_BOOKING_ENABLED=.*/SOCIAL_BOOKING_ENABLED=true/' /var/www/mywave/.env
sudo bash /var/www/mywave/automation/production/prod_env_permissions_fix.sh
sudo bash /var/www/mywave/automation/production/prod_env_readable_check.sh
sudo bash /var/www/mywave/automation/production/prod_import_as_run_user.sh
sudo systemctl restart mywave-site
sudo bash /var/www/mywave/automation/production/prod_pr56_smoke.sh --phase-b
```

### 4. Manual assign smoke (Owner)

```bash
# Without token → 401
curl -sS -o /dev/null -w '%{http_code}\n' \
  -X POST http://127.0.0.1:5000/api/social/sessions/assign \
  -H 'Content-Type: application/json' \
  -d '{"application_id":"soc_app_...","session_date":"2026-07-15","session_time":"10:00","assigned_by":"trainer"}'

# With token → 201 (use real application_id from Social_Applications)
curl -sS -X POST http://127.0.0.1:5000/api/social/sessions/assign \
  -H "X-Admin-Token: \$ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"application_id":"soc_app_...","session_date":"2026-07-15","session_time":"10:00","assigned_by":"trainer"}'
```

Verify in Sheets: `Social_Sessions` row + `Social_Audit_Log` entries. Telegram: sanitized, no health details.

---

## Rollback

### Code rollback (PR56 → PR55)

```bash
cd /var/www/mywave
sudo -u www-data git reset --hard c35d19cc
sudo bash automation/production/prod_env_permissions_fix.sh
sudo bash automation/production/prod_import_as_run_user.sh
sudo systemctl restart mywave-site
```

### Permission-only rollback (site 502)

**Do this first** before code rollback:

```bash
sudo bash automation/production/prod_env_permissions_fix.sh
sudo bash automation/production/prod_import_as_run_user.sh
sudo systemctl restart mywave-site
journalctl -u mywave-site -n 50 --no-pager
```

---

## 502 / gunicorn status=3 triage

```text
1. journalctl -u mywave-site -n 80 --no-pager
2. Look for PermissionError on .env
3. prod_env_permissions_fix.sh
4. prod_import_as_run_user.sh
5. Only then consider code rollback
```

---

## Regression checklist

| Check | Phase A | Phase B |
|-------|---------|---------|
| `/health/live` | ok | ok |
| `/health/ready` | ok | ok |
| `/social` | 200 | 200 |
| `/api/calendar/slots` | 200 | 200 |
| assign without flag | 503 | — |
| assign without token | — | 401 |
| assign with token | — | 201 |
| Public `/social` no calendar write | yes | yes |
| Commercial booking unchanged | yes | yes |
