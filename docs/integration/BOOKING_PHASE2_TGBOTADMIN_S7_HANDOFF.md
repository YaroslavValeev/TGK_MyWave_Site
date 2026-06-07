# BOOKING Phase 2 — TGbotAdmin S7 Handoff

**From:** Site MyWave  
**To:** TGbotAdmin  
**Date:** 2026-06-08  
**Site Git HEAD:** `1ecbd161`  
**GM status:** Site staging S5/S8/S9 **PASS** — **S7 pending TGbotAdmin**

---

## 1. Staging resources (read-only audit)

| Resource | Value |
|----------|--------|
| **Staging root** | `/var/www/mywave-staging` |
| **Site URL (internal)** | `http://127.0.0.1:5002` |
| **Calendar ID** | `e4ab0adc25a259eebdf83a506073dd5874dee79890b038f924f164703d187dec@group.calendar.google.com` |
| **Calendar name** | `StagingMyWave` |
| **Spreadsheet ID** | `16Ewm8Npv3bkNH37X-KAm3PWmRedQ1a8xoiO6LPggyBI` |
| **Spreadsheet name** | MyWave Staging Booking |
| **Phase 2 flags** | all `BOOKING_PHASE2_*=1` on staging only |

**Do not use production Calendar/Sheet IDs for S7.**

---

## 2. Artifact: `s8_calendar.json`

**Location on staging host:** `/tmp/s8_calendar.json`  
**Regenerate (if missing):**

```bash
cd /var/www/mywave-staging
source venv/bin/activate
export STAGING_ROOT=/var/www/mywave-staging
export S8_DATE="2026-06-12"
python3 automation/staging/s8_calendar_dump.py | tee /tmp/s8_calendar.json
```

**PASS marker:** JSON `"s8_pass": true` and stdout `S8_ok`.

### 2.1 S8 summary (Calendar API, date `2026-06-12`)

| Event | Expected (Site) | S8 check |
|-------|-----------------|----------|
| Boat `07:00` | 90 min, location `Катер`, `set_count=3`, summary v2 with `WEB_ID:` and «сет» | **PASS** |
| Gym `16:00` | 90 min, location `Зал`, summary v2 with `WEB_ID:` and `Зал` | **PASS** |

TGbotAdmin: verify parser compatibility with summary v2 format and `(WEB_ID: bk_…)` vs legacy `(ID: …)`.

---

## 3. S5 travel buffer — summary

**Evidence:** `/tmp/s5_final.log` on staging host  
**Run:** 2026-06-08 ~01:59 MSK  
**Script:** `automation/staging/s5_api_smoke.py` @ `1ecbd161`  
**Result:** `S5_ok`

| Part | Date | Anchor | Expected buffer | Actual |
|------|------|--------|-----------------|--------|
| **B** gym→boat | `2026-06-13` | gym `10:00` (90 min) | boat before `13:30` blocked; `13:30` available | `boat_12_blocked True`, `boat_1330_available True` |
| **A** boat→gym | `2026-06-27` | boat `12:00` (30 min) | gym before `14:30` blocked; `14:30` available | `gym_14_blocked True`, `gym_1430_available True` |

Travel buffer rule: **120 min** between gym end and boat start (and reverse).

---

## 4. S9 orphan audit — summary

**Evidence:** `/tmp/s9_final.log` on staging host  
**Run:** 2026-06-08 ~01:59 MSK  
**Script:** `automation/staging/s9_orphan_check.py`

| Field | Value |
|-------|--------|
| **Spreadsheet checked** | `16Ewm8Npv3bkNH37X-KAm3PWmRedQ1a8xoiO6LPggyBI` (staging only) |
| **orphan_count** | `0` |
| **Result** | `S9_ok` |

Definition: no active `Workouts` row without matching `Client_Workouts` row.

---

## 5. S7 scope (TGbotAdmin)

| Check | Description |
|-------|-------------|
| Staging calendar | Point bot/admin read path to staging Calendar ID above |
| WEB marker | Web booking → summary contains `(WEB_ID: bk_…)` |
| TG marker | Bot booking → summary contains `(ID: …)` |
| False duplicate | WEB_ID must not be treated as duplicate of TG `(ID: …)` |
| Parser | Confirm v2 summary / location / duration parsing on staging events |

**Site verdict:** staging checks ready for TGbotAdmin S7.  
**Prod:** not in scope until S7 PASS + GM approval.

---

## 6. Guardrails (unchanged)

Until GM prod rollout approval:

- Do **not** change production `.env` or enable prod `BOOKING_PHASE2_*`
- Do **not** restart `mywave-site`, `mywave-node.service`, `mywave-telegram-bot.service` for Phase 2
- Do **not** touch TGbotAdmin **production** config for this audit

---

## 7. References

- Full Site report: [`BOOKING_PHASE2_STAGING_E2E_REPORT_2026-06-07.md`](BOOKING_PHASE2_STAGING_E2E_REPORT_2026-06-07.md)
- Close-out commands: [`BOOKING_PHASE2_STAGING_CLOSEOUT_COMMANDS.md`](BOOKING_PHASE2_STAGING_CLOSEOUT_COMMANDS.md)
- Calendar contract v2: [`BOOKING_CALENDAR_EVENT_CONTRACT_v2.md`](BOOKING_CALENDAR_EVENT_CONTRACT_v2.md)
