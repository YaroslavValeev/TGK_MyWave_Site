# BOOKING_PHASE2_PR18 — Production Deploy Package (flags OFF)

**PR:** #18 — merged
**PR link:** https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/18
**Merge commit (`main`):** `7b8ecb66cbb958416c99cdb0576cdb0ac089d4ee`
**Pre-PR18 baseline:** `501aa59e2891b516c8279c8111490f46ab3a9936`
**Status:** merge **DONE** — deploy **awaiting separate GM approval**
**Policy:** flags OFF; compensation B active without feature flag

---

## 1. Merge confirmation

| Item | Value |
|------|-------|
| PR #18 merged | **YES** |
| Merge commit | `7b8ecb66cbb958416c99cdb0576cdb0ac089d4ee` |
| HEAD after merge | `7b8ecb66cbb958416c99cdb0576cdb0ac089d4ee` |

---

## 2. Final file list (vs `501aa59e`)

```
app/routes/calendar_routes.py
app/services/booking/__init__.py
app/services/booking/calendar_writer.py
app/services/booking/pipeline.py
app/services/booking/sheets_writer.py
tests/unit/test_booking_sheets_compensation.py
docs/integration/BOOKING_PHASE2_SHEETS_COMPENSATION_PACKAGE.md
docs/integration/BOOKING_PHASE2_PR18_MERGE_PACKAGE.md
docs/operations/BOOKING_SHEETS_ORPHAN_CLEANUP_RUNBOOK.md
```

---

## 3. Exact test command (prod host, before restart)

```bash
cd /var/www/mywave
source venv/bin/activate
export SECRET_KEY="${SECRET_KEY:-$(grep -E '^SECRET_KEY=' .env | cut -d= -f2-)}"

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
```

**Expected:** `87 passed`

```bash
grep -E '^BOOKING_PHASE2_' .env || echo "OK: no BOOKING_PHASE2_* in .env"
```

---

## 4. Exact deploy commands (flags OFF)

**Execute only in Owner deploy window after GM deploy approval.**

```bash
sudo MYWAVE_ROOT=/var/www/mywave bash /var/www/mywave/deploy/scripts/backup_mywave.sh

cd /var/www/mywave
git fetch --all --prune
git checkout main
git pull --ff-only origin main

git rev-parse HEAD
# Expected: 7b8ecb66cbb958416c99cdb0576cdb0ac089d4ee

grep -E '^BOOKING_PHASE2_' .env || echo "OK: no BOOKING_PHASE2_* in .env"

source venv/bin/activate
export SECRET_KEY="${SECRET_KEY:-$(grep -E '^SECRET_KEY=' .env | cut -d= -f2-)}"

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

sudo systemctl restart mywave-site
```

### Do NOT run

```bash
sudo systemctl restart mywave-node.service
sudo systemctl restart mywave-telegram-bot.service
```

### Do NOT add to `.env` without separate approval

```bash
BOOKING_PHASE2_AVAILABILITY=1
BOOKING_PHASE2_TRAVEL_BUFFER=1
BOOKING_PHASE2_MULTI_SET_BOAT=1
BOOKING_PHASE2_SUMMARY_V2=1
BOOKING_PHASE2_GYM_LOCATION_V2=1
```

---

## 5. Exact post-deploy smoke commands

Wait **5–10 s** after restart:

```bash
sudo systemctl is-active mywave-site
sudo systemctl status mywave-site --no-pager -l | head -20

curl -fsS https://mywavewake.ru/health
curl -fsS -o /dev/null -w "home %{http_code}\n" https://mywavewake.ru/
curl -fsS -o /dev/null -w "robots %{http_code}\n" https://mywavewake.ru/robots.txt
curl -fsS -o /dev/null -w "privacy %{http_code}\n" https://mywavewake.ru/privacy
curl -fsS -o /dev/null -w "offer %{http_code}\n" https://mywavewake.ru/offer

sudo journalctl -u mywave-site --since "5 min ago" --no-pager | grep -E 'booking_sheets_partial_failure|compensate_workout_row' || echo "OK: no compensation events in window"

sudo journalctl -u mywave-site --since "5 min ago" --no-pager | tail -40
```

**Expected:**

- `mywave-site` active
- `/health`, `/`, `/robots.txt`, `/privacy`, `/offer` — HTTP 200
- All `BOOKING_PHASE2_*` absent or `0`
- No compensation log lines unless partial failure occurred during window

---

## 6. Rollback command

**Pre-PR18 production commit:** `501aa59e2891b516c8279c8111490f46ab3a9936`

```bash
cd /var/www/mywave
git fetch --all --prune
git checkout 501aa59e2891b516c8279c8111490f46ab3a9936

source venv/bin/activate
export SECRET_KEY="${SECRET_KEY:-$(grep -E '^SECRET_KEY=' .env | cut -d= -f2-)}"

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
  -q --tb=short

sudo systemctl restart mywave-site
```

Alternative (keep history): `git revert -m 1 7b8ecb66cbb958416c99cdb0576cdb0ac089d4ee` then pull + pytest + restart `mywave-site` only.

---

## 7. Explicit confirmations

| Confirmation | Status |
|--------------|--------|
| Restart **only** `mywave-site` | Required on deploy |
| **Do not** restart `mywave-node.service` | Confirmed |
| **Do not** restart `mywave-telegram-bot.service` | Confirmed |
| Production flags ON **not approved** | Confirmed |
| `.env` **not changed** by PR #18 | Confirmed |
| Production deploy | **Not executed** — awaiting deploy approval |

---

## Related

- [`BOOKING_PHASE2_PR18_MERGE_PACKAGE.md`](BOOKING_PHASE2_PR18_MERGE_PACKAGE.md)
- [`BOOKING_SHEETS_ORPHAN_CLEANUP_RUNBOOK.md`](../operations/BOOKING_SHEETS_ORPHAN_CLEANUP_RUNBOOK.md)
