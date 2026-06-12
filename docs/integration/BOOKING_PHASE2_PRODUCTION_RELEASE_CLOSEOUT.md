# BOOKING Phase 2 — Production Release Closeout (Site)

**Status:** **FINAL PASS / CLOSED**  
**Date:** 2026-06-12  
**Audience:** Site / GM / TGbotAdmin (internal)

---

## 1. Final production state

| Item | Value |
|------|--------|
| **Release verdict** | Production Phase 2 rollout: **FINAL PASS / CLOSED** |
| **Site HEAD** | `df26212d06a130c0ff536b27d0b957e60d55219f` (`df26212d`) |
| **Latest restart** | `Fri 2026-06-12 01:43:42 MSK` (`mywave-site` only) |
| **Service** | `mywave-site`: active |

### Final flags (all ON)

```text
BOOKING_PHASE2_AVAILABILITY=1
BOOKING_PHASE2_TRAVEL_BUFFER=1
BOOKING_PHASE2_MULTI_SET_BOAT=1
BOOKING_PHASE2_SUMMARY_V2=1
BOOKING_PHASE2_GYM_LOCATION_V2=1
```

### Rollout steps (accepted)

| Step | Flag | Status |
|------|------|--------|
| 1 | `AVAILABILITY=1` | PASS |
| 2 | `TRAVEL_BUFFER=1` | PASS |
| 3 | `MULTI_SET_BOAT=1` | PASS |
| 4 | `SUMMARY_V2=1` | PASS |
| 5 | `GYM_LOCATION_V2=1` | PASS (after hotfix `df26212d`) |

---

## 2. Final evidence paths (prod host)

| Artifact | Path |
|----------|------|
| Step 5 retry log | `/tmp/step5_retry_20260612_014312.log` |
| Hotfix deploy log | `/tmp/step5_hotfix_code_only_complete_20260612_005430.log` |
| Hotfix verify | `/tmp/step5_hotfix_code_only_verify_safe_20260612_011147.txt` |
| Rollback backup | `/var/backups/mywave/.env.step5_retry_20260612_014312` |

Earlier accepted evidence (archive):

- Step 4: `/var/backups/mywave/step4_evidence_20260611_015433.tar.gz`
- Step 5 rollback: `/tmp/gm_step5_rollback_summary_20260612_000552.txt`

---

## 3. Runtime acceptance (final)

- `/health`: HTTP 200, database OK, google OK (degraded = optional checks only)
- Routes: `/` 200, `/blog` 200, `/booking` 308
- Boat slots: OK, `max_set_count` present
- Gym slots: OK
- Writer dry-run: `gym_loc=Зал`, `boat_loc=Катер`, `(WEB_ID: ...)` web, `(ID: tg_id)` Telegram unchanged
- No hard ImportError / Traceback / circular-import regression after hotfix

---

## 4. Observe mode (post-close)

**No further server changes** under this rollout:

- do not change `.env`, Phase 2 flags, Calendar/Sheet IDs
- do not restart `mywave-node`, `mywave-telegram-bot`
- do not touch `/opt/mywave-bot`
- do not run bundle rollout, production test bookings, or `.env` dedupe

Read-only check (optional):

```bash
cd /var/www/mywave
grep -E '^BOOKING_PHASE2_' .env
systemctl is-active mywave-site
curl -fsS https://mywavewake.ru/health
```

---

## 5. Rollback reference (GM-approved only)

Return to Step 4 state (disable Step 5 only):

```bash
cp -a /var/backups/mywave/.env.step5_retry_20260612_014312 .env
# ensure GYM_LOCATION_V2=0 in restored file
systemctl restart mywave-site
```

Steps 1–4 remain ON in backup taken before Step 5 retry.

---

## 6. Known non-blocking backlog (Site)

Track separately — **not** part of closed Phase 2 rollout:

| Item | Classification |
|------|----------------|
| `blog_post` table missing | Site backlog |
| `parser_news_sheet` / blog-store Sheets read error | Site backlog |
| Socket / invalid session / `Bad file descriptor` logs | Site backlog |

---

## 7. Separate tracks (not in this release)

| Track | Owner | Notes |
|-------|-------|-------|
| P1 Telegram Calendar notification defect (`Неизвестно`, gym/boat map mismatch) | TGbotAdmin | `(ID: tg_id)` events; not Site Phase 2 regression |
| Payment / booking UX improvements | Future | Out of scope |
| `.env` dedupe (duplicate Sheet/Calendar lines) | Future GM approval | WARN only during rollout |

---

## 8. Security reminder

- Do **not** redistribute raw `.env` or unsanitized terminal logs (may contain service tokens).
- If secrets appeared in shared logs during rollout, rotate per security policy after release close.
- Use evidence summaries and sanitized paths in external comms.

---

## 9. Key commits (reference)

| Commit | Purpose |
|--------|---------|
| `7cc11265` | Pre-Phase-2 rollout baseline on prod |
| `18938153` | Venue map URLs (Step 5 prep; caused circular import on first Step 5 attempt) |
| `df26212d` | **Final prod HEAD** — circular-import hotfix via `booking_location_constants.py` |

---

**Site statement:** Production Phase 2 booking flags rollout is **closed**. Production remains in **observe mode** unless GM opens a new change window.
