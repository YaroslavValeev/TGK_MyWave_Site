# BOOKING_PHASE2_PR18 — Final Merge / Release Package

**PR:** #18 — Partial Sheets B+E (compensation + orphan runbook)
**Branch:** `feature/booking-phase2-sheets-compensation`
**PR link:** https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/18

| Commit | Hash | Note |
|--------|------|------|
| **PR HEAD (final)** | `ed200bf7b91c1bb7e98ab4c7b89a1623476b1136` | Docs whitespace cleanup |
| Reviewed functional+tests | `3358c329952a6cf1362a7bb274e10de302ef2c12` | GM matrix tests |
| **Functional (B+E)** | `f312e9764b81a3f66a45cedf8a84648f04275b5b` | Compensation + runbook |
| Pre-PR18 `main` | `501aa59e2891b516c8279c8111490f46ab3a9936` | PR #17 deploy doc (prod baseline) |

**CI:** green (`quality-checks` pass)
**Tests:** `87 passed` (81 booking suite + 6 compensation)
**TGbotAdmin:** re-check **PASS** — **MERGE ALLOWED WITH FOLLOW-UP**
**Blockers:** **0**
**GM merge:** **awaiting separate approval** — PR **not merged yet**

**Policy:** Phase 2 runtime **flags OFF** on prod; compensation B is **always active** (no feature flag). Flags ON — отдельное approval после staging E2E.

---

## 0. Review summary

| Reviewer | Result | Blockers |
|----------|--------|----------|
| GM (functional) | **PASS** — APPROVED FOR CODE REVIEW | 0 |
| TGbotAdmin (initial) | CHANGES REQUESTED | trailing whitespace in docs |
| TGbotAdmin (re-check) | **PASS** — MERGE ALLOWED WITH FOLLOW-UP | **0** |

**Confirmed:** functional/test code after `3358c329` unchanged; cleanup commit `ed200bf7` — docs only.

---

## 1. PR #18 review result

**PASS** — ready for GM merge approval (not merged until explicit approval).

---

## 2. Final PR head commit

```
ed200bf7b91c1bb7e98ab4c7b89a1623476b1136
```

---

## 3. Final file list (8 paths vs `501aa59e`)

```
app/routes/calendar_routes.py
app/services/booking/__init__.py
app/services/booking/calendar_writer.py
app/services/booking/pipeline.py
app/services/booking/sheets_writer.py
docs/integration/BOOKING_PHASE2_SHEETS_COMPENSATION_PACKAGE.md
docs/operations/BOOKING_SHEETS_ORPHAN_CLEANUP_RUNBOOK.md
tests/unit/test_booking_sheets_compensation.py
```

**Out of scope:** prod `.env`, `mywave-node`, `mywave-telegram-bot`, TGbotAdmin code.

---

## 4. CI status

| Check | Status |
|-------|--------|
| `quality-checks` | **pass** |

`git diff --check origin/main...HEAD` — **PASS**

---

## 5. Test command / output

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

**GM scenarios covered:**

| # | Scenario | Test |
|---|----------|------|
| 1 | Client_Workouts fail → compensation | `test_client_workout_fail_compensates_workout_and_calendar` |
| 2 | Compensation mark fail → SheetsBookingError | `test_compensation_mark_fail_still_raises_sheets_error` |
| 3 | Calendar delete fail → error + log | `test_calendar_delete_fail_still_raises_sheets_error` |
| 4 | Happy path | `test_success_no_compensation` |
| 5 | Calendar fail → no Sheets | `test_calendar_fail_still_no_sheets` |

```bash
grep -E '^BOOKING_PHASE2_' .env || echo "OK: no BOOKING_PHASE2_* in .env"
```

---

## 6. Rollback plan

| Scenario | Action |
|----------|--------|
| Pre-PR18 production | `501aa59e` (current `main` before PR #18 merge) |
| After deploy | `git revert <merge-commit>` or `git checkout 501aa59e` + pull prod + pytest + **restart `mywave-site` only** |
| Runtime effect | Compensation disabled → partial Sheets failure may leave orphan Workouts (pre-B behavior); runbook E remains valid for manual cleanup |

**No DB migration.** **No `.env` change required for deploy or rollback.**

---

## 7. Production deploy commands (flags OFF)

**Execute only in Owner deploy window, after GM merge approval + merge to `main`.**

```bash
sudo MYWAVE_ROOT=/var/www/mywave bash /var/www/mywave/deploy/scripts/backup_mywave.sh

cd /var/www/mywave
git fetch --all --prune
git checkout main
git pull --ff-only origin main

git rev-parse HEAD
# Expected: merge commit containing f312e976 (Partial Sheets B+E)

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
  -q

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

## 8. Post-deploy smoke (flags OFF)

Wait **5–10 s** after restart:

```bash
sudo systemctl is-active mywave-site
sudo systemctl status mywave-site --no-pager -l | head -20

curl -fsS https://mywavewake.ru/health
curl -fsS -o /dev/null -w "home %{http_code}\n" https://mywavewake.ru/
curl -fsS -o /dev/null -w "robots %{http_code}\n" https://mywavewake.ru/robots.txt
curl -fsS -o /dev/null -w "privacy %{http_code}\n" https://mywavewake.ru/privacy
curl -fsS -o /dev/null -w "offer %{http_code}\n" https://mywavewake.ru/offer

# Compensation log marker (should NOT appear unless partial failure occurred)
sudo journalctl -u mywave-site --since "5 min ago" --no-pager | grep -E 'booking_sheets_partial_failure|compensate_workout_row' || echo "OK: no compensation events in window"

sudo journalctl -u mywave-site --since "5 min ago" --no-pager | tail -40
```

**Expected:**

- `mywave-site` active
- `/health`, `/`, `/robots.txt`, `/privacy`, `/offer` — HTTP 200
- `/health` degraded only for optional services (if applicable)
- All `BOOKING_PHASE2_*` absent or `0`
- Booking happy path unchanged (flags OFF UX from PR #17)
- Compensation active silently (no flag); only visible on partial Sheets failure → HTTP 500 + log `booking_sheets_partial_failure`

---

## 9. Explicit confirmations (pre/post deploy)

| Confirmation | Status |
|--------------|--------|
| PR #18 review: **PASS** | TGbotAdmin re-check PASS |
| Restart **only** `mywave-site` | Required on deploy |
| **Do not** restart `mywave-node.service` | Confirmed |
| **Do not** restart `mywave-telegram-bot.service` | Confirmed |
| Production flags ON **not approved** | Confirmed — keep OFF |
| `.env` **not changed** by this PR | Confirmed |
| TGbotAdmin code **not touched** | Confirmed |
| Production deploy **not executed** until GM approval | Confirmed |

### Deploy window checklist

- [ ] GM merge approval received
- [ ] PR #18 merged to `main`
- [ ] Backup completed
- [ ] `git rev-parse HEAD` documents merge commit
- [ ] pytest **87 passed** on prod host
- [ ] Restart **only** `mywave-site`
- [ ] **Did not** restart `mywave-node.service`
- [ ] **Did not** restart `mywave-telegram-bot.service`
- [ ] Production flags **OFF** / absent in `.env`
- [ ] Post-deploy smoke PASS

---

## 10. Production impact (flags OFF deploy)

| Statement | Status |
|-----------|--------|
| Partial Sheets compensation (Option B) | **Active always** — no feature flag |
| Orphan runbook (Option E) | Documented — ops only |
| `SheetsBookingError` → HTTP 500 | Active on partial journal failure |
| Phase 2 availability / multi-set / recheck | Active only when flags ON |
| All `BOOKING_PHASE2_*` default OFF | YES |

---

## 11. Follow-up (after merge + deploy)

| Item | Track |
|------|-------|
| Staging E2E | [`BOOKING_PHASE2_STAGING_E2E_PACKAGE.md`](BOOKING_PHASE2_STAGING_E2E_PACKAGE.md) — **mandatory** before flags ON |
| Prod flags ON | Separate GM approval only |
| Orphan audit | Runbook [`BOOKING_SHEETS_ORPHAN_CLEANUP_RUNBOOK.md`](../operations/BOOKING_SHEETS_ORPHAN_CLEANUP_RUNBOOK.md) — pre-staging optional |

---

## 12. Related packages

- [`BOOKING_PHASE2_SHEETS_COMPENSATION_PACKAGE.md`](BOOKING_PHASE2_SHEETS_COMPENSATION_PACKAGE.md)
- [`BOOKING_PHASE2_PR17_MERGE_PACKAGE.md`](BOOKING_PHASE2_PR17_MERGE_PACKAGE.md) — prod baseline (PR #17 GREEN)
- [`BOOKING_PARTIAL_SHEETS_FOLLOWUP.md`](BOOKING_PARTIAL_SHEETS_FOLLOWUP.md)
