# BOOKING Phase 2 — Production CODE-ONLY Deploy Package (flags OFF)

**From:** Site MyWave  
**To:** GM / Owner  
**Date:** 2026-06-09  
**Status:** **PLAN ONLY — await GM deploy approval before execution**  
**Purpose:** Unblock Phase 2 flag Step 1 pre-flight (`HEAD >= 27f2d886`)  
**Policy:** **no `.env` changes**, **no `BOOKING_PHASE2_*`**, restart **`mywave-site` only**

---

## 0. Executive summary

| Item | Value |
|------|--------|
| **Current production HEAD** | `67b30510ae948f8e7e8d457510dde35090f25e2a` |
| **Deploy target (`origin/main`)** | `e71839e250107a9d8d5847d6b51f0a4d5208af3e` |
| **Target message** | `chore(prod): read-only Phase 2 preflight with safe.directory` |
| **Rollout baseline (minimum)** | `27f2d8869ddb269f09e081aa7d10694fb65ee844` |
| **Runtime code delta** | **None** (`app/`, `static/`, `templates/`, `migrations/` unchanged) |
| **What changes on disk** | `automation/*`, `docs/integration/*`, `deploy/systemd/mywave-staging.service` (staging unit only; prod unaffected unless enabled) |
| **Phase 2 booking runtime** | Already present at `67b30510` (flags default OFF in code) |
| **After deploy** | Re-run `automation/production/phase2_preflight_readonly.sh` → expect `PREFLIGHT_OK` |

---

## 1. Why this deploy is required

Production pre-flight **FAIL** because:

1. Local git history stops at `67b30510` — object `27f2d886` not present until `git fetch` + `pull`.
2. `git fetch` as `www-data` fails: `Permission denied` on `.git/FETCH_HEAD`.
3. GM gate for flag Step 1 requires `merge-base --is-ancestor 27f2d886 HEAD`.

This deploy **does not** enable Phase 2 behavior — it syncs repo artifacts and git objects only.

---

## 2. Backup commands (mandatory, step 1)

```bash
TS="$(date +%Y%m%d_%H%M%S)"
export MYWAVE_ROOT=/var/www/mywave

# Automated backup
sudo MYWAVE_ROOT=/var/www/mywave \
  BACKUP_ROOT=/var/backups/mywave \
  BACKUP_KEEP_DAYS=7 \
  bash /var/www/mywave/deploy/scripts/backup_mywave.sh

# Manual snapshots
cp -a /var/www/mywave/.env "/var/backups/mywave/.env.pre_code_deploy_${TS}"
chmod 600 "/var/backups/mywave/.env.pre_code_deploy_${TS}"

cd /var/www/mywave
git -c safe.directory=/var/www/mywave rev-parse HEAD | tee "/var/backups/mywave/head.pre_code_deploy_${TS}.txt"
grep -E '^(GOOGLE_CALENDAR_ID|SPREADSHEET_ID|BOOKING_PHASE2_)' .env \
  | tee "/var/backups/mywave/env_booking.pre_code_deploy_${TS}.txt"
curl -fsS https://mywavewake.ru/health | tee "/var/backups/mywave/health.pre_code_deploy_${TS}.json"

echo "backup_ts=${TS}"
```

**Rollback anchor:** `67b30510ae948f8e7e8d457510dde35090f25e2a` + `.env.pre_code_deploy_${TS}`

---

## 3. Git permission / FETCH_HEAD fix

**Do not run:** `git config --global safe.directory …`

### 3.1 Recommended: deploy git as root with per-invocation safe.directory

Root can fetch/pull without `www-data` writing `FETCH_HEAD` issues when using:

```bash
GIT="git -c safe.directory=/var/www/mywave"
sudo $GIT -C /var/www/mywave fetch origin main
sudo $GIT -C /var/www/mywave pull --ff-only origin main
```

### 3.2 Verify remote before pull (read-only)

```bash
git -c safe.directory=/var/www/mywave ls-remote origin refs/heads/main
```

**Expected:** `e71839e250107a9d8d5847d6b51f0a4d5208af3e` (or newer on `main`).

### 3.3 Optional post-deploy fix (future www-data fetch)

Only if Owner wants `www-data` to run `git fetch` later:

```bash
sudo chown -R www-data:www-data /var/www/mywave/.git
```

**Not required** for this deploy if root performs fetch/pull (§4).

---

## 4. Exact target commit

| Field | Value |
|-------|--------|
| **Target SHA** | `e71839e250107a9d8d5847d6b51f0a4d5208af3e` |
| **Short** | `e71839e2` |
| **Branch** | `main` |
| **Includes baseline** | `27f2d886` ✅ (ancestor of `e71839e2`) |
| **Includes rollout package** | `91965cfd` ✅ |
| **Includes preflight script** | `e71839e2` ✅ |

If `origin/main` advanced after this document: deploy **latest `origin/main`** only if `git diff --stat 67b30510..origin/main -- app/ static/ templates/ migrations/` remains empty or GM reviews delta.

---

## 5. Code-only deploy commands (execute after GM approval)

```bash
set -euo pipefail
export PROD_ROOT=/var/www/mywave
export TARGET_SHA=e71839e250107a9d8d5847d6b51f0a4d5208af3e
GIT="git -c safe.directory=${PROD_ROOT}"

cd "${PROD_ROOT}"

echo "=== Pre: HEAD and flags ==="
${GIT} rev-parse HEAD
grep -E '^BOOKING_PHASE2_' .env && echo "STOP: unexpected flags" && exit 1 || echo "OK: no BOOKING_PHASE2_*"

echo "=== Fetch + pull ==="
${GIT} fetch origin main
${GIT} rev-parse origin/main
${GIT} pull --ff-only origin main

DEPLOYED="$(${GIT} rev-parse HEAD)"
echo "deployed=${DEPLOYED}"
test "${DEPLOYED}" = "${TARGET_SHA}" || echo "WARN: HEAD != documented target (may be newer main)"

echo "=== Baseline gate ==="
${GIT} merge-base --is-ancestor 27f2d8869ddb269f09e081aa7d10694fb65ee844 HEAD \
  && echo "PASS: HEAD >= rollout baseline 27f2d886" \
  || (echo "FAIL: baseline gate" && exit 1)

echo "=== .env unchanged check (BOOKING_PHASE2 + effective IDs) ==="
grep -E '^BOOKING_PHASE2_' .env && exit 1 || echo "OK: flags still absent"
grep -E '^SPREADSHEET_ID=' .env | tail -1
grep -E '^GOOGLE_CALENDAR_ID=' .env | tail -1

echo "=== pytest (flags OFF in .env; conftest forces OFF in tests) ==="
source venv/bin/activate
export SECRET_KEY="$(grep -E '^SECRET_KEY=' .env | tail -1 | cut -d= -f2-)"

python -m pytest \
  tests/unit/test_booking_grid.py \
  tests/unit/test_booking_pipeline_phase2.py \
  tests/unit/test_booking_features.py \
  tests/unit/test_booking_calendar_v2.py \
  tests/unit/test_booking_calendar_reader_buffer.py \
  tests/unit/test_booking_availability_phase2.py \
  tests/unit/test_booking_phase1.py \
  tests/unit/test_booking_orchestrator_context.py \
  tests/unit/test_booking_service.py \
  tests/unit/test_boat_slots.py \
  tests/unit/test_booking_sheets_compensation.py \
  -q --tb=short

echo "=== Restart mywave-site ONLY ==="
sudo systemctl restart mywave-site
sleep 8
sudo systemctl is-active mywave-site
```

### 5.1 Explicit confirmations during deploy

| # | Confirmation |
|---|--------------|
| 1 | **`.env` file not edited** (no `nano`, no `sed` on `.env`) |
| 2 | **`BOOKING_PHASE2_*` remain absent** (or `=0` if already present) |
| 3 | **`GOOGLE_CALENDAR_ID` / `SPREADSHEET_ID` not changed** |
| 4 | **No** `flask db upgrade` required (no migration changes in delta) |
| 5 | **No** `pip install` required unless `requirements.txt` changed (it did not) |
| 6 | Restart **only** `mywave-site` |

### 5.2 Do NOT run

```bash
sudo systemctl restart mywave-node.service
sudo systemctl restart mywave-telegram-bot.service
sudo systemctl enable mywave-staging   # staging unit shipped in repo; do not enable on prod path
# Do not add BOOKING_PHASE2_* to .env
```

---

## 6. Post-deploy smoke (flags OFF)

Wait **5–10 s** after restart.

```bash
export PROD_URL=https://mywavewake.ru
export SMOKE_DATE="$(date -d '+14 days' +%Y-%m-%d 2>/dev/null || python3 -c 'from datetime import date,timedelta; print((date.today()+timedelta(days=14)).isoformat())')"

echo "smoke_date=${SMOKE_DATE}"

sudo systemctl is-active mywave-site
sudo systemctl status mywave-site --no-pager -l | head -20

curl -fsS "${PROD_URL}/health" | python3 -m json.tool
curl -fsS -o /dev/null -w "home %{http_code}\n" "${PROD_URL}/"
curl -fsS -o /dev/null -w "robots %{http_code}\n" "${PROD_URL}/robots.txt"
curl -fsS -o /dev/null -w "privacy %{http_code}\n" "${PROD_URL}/privacy"
curl -fsS -o /dev/null -w "offer %{http_code}\n" "${PROD_URL}/offer"
```

### 6.1 Basic booking / slots smoke (Phase 1 path, read-only GET)

```bash
curl -fsS "${PROD_URL}/api/calendar/slots/${SMOKE_DATE}?service=boat" \
  | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert isinstance(d,list), d
times=[x.get('time') for x in d]
print('boat_slots', len(times), 'first', times[0] if times else None, 'last', times[-1] if times else None)
"

curl -fsS "${PROD_URL}/api/calendar/slots/${SMOKE_DATE}?service=gym" \
  | python3 -c "
import json,sys
d=json.load(sys.stdin)
print('gym_slots', len(d) if isinstance(d,list) else d)
"
```

**PASS expectations (flags OFF / Phase 1):**

- `/health` HTTP **200**; `database` OK; `google` OK
- `/`, `/robots.txt`, `/privacy`, `/offer` HTTP **200**
- Boat/gym slots endpoints HTTP **200** with JSON list (may be empty on unscheduled days — retry a known gym schedule day)
- **No** `BOOKING_PHASE2_*` in `.env`
- **No** new compensation errors in journal (§6.2)

### 6.2 Logs (5 min window)

```bash
sudo journalctl -u mywave-site --since "5 min ago" --no-pager \
  | grep -E 'booking_sheets_partial_failure|compensate_workout_row|Traceback|ERROR' \
  | tail -30 || echo "OK: no critical booking errors in window"

sudo journalctl -u mywave-site --since "5 min ago" --no-pager | tail -40
```

---

## 7. Post-deploy read-only pre-flight (required)

```bash
bash /var/www/mywave/automation/production/phase2_preflight_readonly.sh \
  | tee /tmp/prod_phase2_preflight_post_code_deploy.log
```

**PASS:** last line `PREFLIGHT_OK` including:

- `PASS: HEAD >= rollout baseline 27f2d886`
- `origin/main` matches deployed SHA
- flags absent
- health HTTP 200

Attach `/tmp/prod_phase2_preflight_post_code_deploy.log` to GM for Step 1 flag approval consideration.

---

## 8. Rollback to `67b30510`

**When:** health not 200; pytest fails; unexpected 5xx on booking routes; GM abort.

```bash
set -euo pipefail
ROLLBACK_SHA=67b30510ae948f8e7e8d457510dde35090f25e2a
GIT="git -c safe.directory=/var/www/mywave"

cd /var/www/mywave

# Restore .env only if it was accidentally modified
# cp -a /var/backups/mywave/.env.pre_code_deploy_YYYYMMDD_HHMMSS /var/www/mywave/.env

sudo systemctl stop mywave-site
${GIT} fetch origin main
${GIT} checkout "${ROLLBACK_SHA}"

source venv/bin/activate
export SECRET_KEY="$(grep -E '^SECRET_KEY=' .env | tail -1 | cut -d= -f2-)"

python -m pytest \
  tests/unit/test_booking_grid.py \
  tests/unit/test_booking_pipeline_phase2.py \
  tests/unit/test_booking_features.py \
  tests/unit/test_booking_phase1.py \
  tests/unit/test_boat_slots.py \
  tests/unit/test_booking_sheets_compensation.py \
  -q --tb=short

sudo systemctl start mywave-site
sleep 8
curl -fsS https://mywavewake.ru/health | python3 -m json.tool

${GIT} rev-parse HEAD
# Expected: 67b30510ae948f8e7e8d457510dde35090f25e2a
```

**Note:** Rollback removes docs/automation/preflight script from disk — acceptable; production runtime returns to known PR18 state.

---

## 9. Guardrails

| Rule | Status |
|------|--------|
| Change production `.env` | **FORBIDDEN** in this deploy |
| Enable `BOOKING_PHASE2_*` | **FORBIDDEN** |
| Phase 2 Step 1 flags | **FORBIDDEN** until separate approval after `PREFLIGHT_OK` |
| Restart `mywave-site` | **Allowed** (required once post-pull) |
| Restart `mywave-node.service` | **FORBIDDEN** |
| Restart `mywave-telegram-bot.service` | **FORBIDDEN** |
| TGbotAdmin production | **FORBIDDEN** |
| Change prod Calendar/Sheet IDs | **FORBIDDEN** |

---

## 10. WARN: duplicate `.env` keys (not fixed in this deploy)

Current production effective values (last-wins):

- `SPREADSHEET_ID=1kyNQVjeLLe4Ra6oWuf84fHqSjUlWXI8MakVMOrCgic0`
- `GOOGLE_CALENDAR_ID=9e6scivqg42qmur04tbnbinm3o@group.calendar.google.com`

Earlier duplicate line `SPREADSHEET_ID=1RJpw2m…` (blog/parser) remains in file.

**This deploy does not dedupe `.env`.** Recommend separate maintenance window **before flag Step 1** (not blocking code-only deploy).

---

## 11. GM approval checklist (before execution)

- [ ] Staging E2E GREEN WITH CAVEAT accepted
- [ ] TGbotAdmin PASS WITH NOTES accepted
- [ ] Rollout package `91965cfd` accepted
- [ ] This code-only package reviewed
- [ ] Maintenance window scheduled
- [ ] Rollback SHA `67b30510` confirmed
- [ ] Owner confirms **no `.env` edit** during deploy

**After successful deploy + `PREFLIGHT_OK`:** GM may consider written approval for **Step 1:** `BOOKING_PHASE2_AVAILABILITY=1` per [`BOOKING_PHASE2_PRODUCTION_FLAG_ROLLOUT_PACKAGE.md`](BOOKING_PHASE2_PRODUCTION_FLAG_ROLLOUT_PACKAGE.md).

---

## 12. References

- Flag rollout (after code deploy): [`BOOKING_PHASE2_PRODUCTION_FLAG_ROLLOUT_PACKAGE.md`](BOOKING_PHASE2_PRODUCTION_FLAG_ROLLOUT_PACKAGE.md)
- Previous prod deploy: [`BOOKING_PHASE2_PR18_DEPLOY_PACKAGE.md`](BOOKING_PHASE2_PR18_DEPLOY_PACKAGE.md)
- Preflight script: `automation/production/phase2_preflight_readonly.sh`
- Staging E2E: [`BOOKING_PHASE2_STAGING_E2E_REPORT_2026-06-07.md`](BOOKING_PHASE2_STAGING_E2E_REPORT_2026-06-07.md)
