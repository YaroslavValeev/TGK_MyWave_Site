# Site Post-Phase-2 Backlog Plan

**Status:** Draft / internal  
**Date:** 2026-06-12  
**Scope:** Non-blocking Site backlog after **Production Phase 2 rollout — FINAL PASS / CLOSED**  
**Mode:** **OBSERVE** — no production changes until GM opens a maintenance window per item

**Related:**

- Closeout: `docs/integration/BOOKING_PHASE2_PRODUCTION_RELEASE_CLOSEOUT.md`
- Prod HEAD (accepted): `df26212d`
- TGbotAdmin: `TGBOTADMIN_NORMAL_MONITORING_AFTER_PHASE2_CLOSE_DONE`

---

## Summary

| ID | Issue | Priority | Prod deploy | Restart |
|----|-------|----------|-------------|---------|
| SITE-BL-001 | `blog_post` table missing on prod SQLite | P2 | Yes (migration/script) | `mywave-site` |
| SITE-BL-002 | `parser_news_sheet` / blog-store Sheets read | P2 | Maybe (code) + env verify | Maybe |
| SITE-BL-003 | Socket / invalid session log noise | P3 | Maybe (config/code) | `mywave-site` if config |
| SITE-BL-004 | Post-release monitoring checklist | P3 | No (read-only script) | No |
| SITE-BL-005 | Security hygiene after rollout exposure | P1 (plan) / P2 (rotate) | No during observe | No during observe |

**Out of scope (separate tracks):** P1 TGbotAdmin calendar defect; payment/booking UX; `.env` dedupe.

---

## SITE-BL-001 — `blog_post` table missing

### Issue

Production SQLite reports `no such table: blog_post` / `sqlite3.OperationalError` when code paths touch the DB fallback (`BlogPost`, admin counts, `db_only` API, chat `blog_post_id` FK).

Observed context:

- Alembic chain on prod is **partially applied**; migration `e89ecaa2c591_add_email_to_user` fails with `NoSuchTableError: user` because `user` was never created by any migration.
- First migration `30bb9011ac3c` creates `blog_post` and `chat_message`, but full `flask db upgrade` cannot complete on prod without a repair strategy.
- Public `/blog` may still return **200** when Sheets path works; DB fallback and admin metrics fail silently or log errors.

### Impact

| Area | Effect |
|------|--------|
| Blog vitrine | Low if Sheets source is healthy |
| DB fallback / offline resilience | **Broken** |
| Admin dashboard blog counts | Error or 0 |
| Chat persistence linking to posts | Degraded |
| Future publish writeback to local cache | Blocked |

### Risk

| Risk | Level | Notes |
|------|-------|-------|
| Running full `flask db upgrade` on prod | **High** | May fail on `user` migration; could leave Alembic in inconsistent state |
| Leaving table absent | Medium | No local blog cache; single point of failure on Sheets |
| Data loss | Low | Sheets remains SoT for blog content |

### Proposed fix

**Phase A — diagnose (read-only, GM-approved SSH):**

```bash
cd /var/www/mywave
sqlite3 instance/mywave.db ".tables" | tr ' ' '\n' | grep -E 'blog_post|chat_message|alembic'
/var/www/mywave/venv/bin/flask db current
```

**Phase B — targeted schema repair (separate maintenance window, not observe mode):**

1. Prefer **surgical create** via existing CLI `flask migrate-blog` (`app/cli/migrate_blog.py`) — adds missing columns to existing `blog_post` if table exists; extend with **create-if-missing** guard if table absent.
2. Alternative: one-off idempotent SQL script (create `blog_post` + `chat_message` per `30bb9011ac3c` only), then stamp Alembic revision or document manual baseline.
3. **Do not** run full upgrade until `user`-chain migrations are made conditional or branched (repo fix: guard `e89ecaa2c591` with `table_exists('user')`).

**Phase C — optional seed:** import publishable rows from Parser News XLSX via `scripts/blog_xlsx_import_to_db.py` (offline backup cache, not replacement for Sheets SoT).

### Test plan

| Step | Where |
|------|-------|
| Unit: migration guards for missing `user` table | CI |
| Staging: `flask db current` + targeted create | Staging |
| `python scripts/chat_persistence_check.py` | Staging |
| `GET /api/blog/posts?db_only=1` returns ≥0 without 500 | Staging → prod |
| Admin blog count loads without exception | Staging |
| Regression: `/blog`, `/blog/<slug>` unchanged | Staging |

### Production deploy required?

**Yes** — for repo migration guard + optional CLI/script update. Schema apply is **server-side DB operation**, not just git pull.

### Restart required?

**Yes** — `systemctl restart mywave-site` after deploy (if app code/CLI changed). DB DDL itself does not require restart if done offline, but verify after restart.

---

## SITE-BL-002 — `parser_news_sheet` / blog-store Sheets read

### Issue

Blog store reads Parser News via `app/services/parser_news_sheet.py` → `read_sheet()`. On prod, symptoms include:

- Empty blog vitrine despite publishable rows in canonical Parser News spreadsheet (`1RJpw2m…`, worksheet `raw_feed`).
- Intermittent read errors under **eventlet** concurrency (greenlet + Google API client), logged from `blog/store.py` / `[parser_news_sheet]`.
- Possible **env misrouting**: legacy `PARSER_TAB` / `SPREADSHEET_ID` pointing at Admin/Tg Bot table instead of `PARSER_NEWS_SPREADSHEET_ID`.

Canonical contract: `env.example` — `PARSER_NEWS_SPREADSHEET_ID` + `PARSER_SHEET_NAME=raw_feed`.

### Impact

| Area | Effect |
|------|--------|
| `/blog`, home preview | Empty or stale cards |
| SEO / content marketing | **High** long-term |
| Booking Phase 2 | **None** (separate subsystem) |
| Publish pipeline | Writeback/read desync if source wrong |

### Risk

| Risk | Level | Notes |
|------|-------|-------|
| Changing `.env` IDs during observe mode | **High** | GM forbids without maintenance window |
| Wrong spreadsheet ID | Medium | Silent empty blog |
| Sheets API quota / concurrent reads | Low–Medium | Transient errors, cache masks partially |

### Proposed fix

**Phase A — read-only diagnostics (observe-safe):**

```bash
cd /var/www/mywave
grep -E '^PARSER_|^SPREADSHEET_ID=' .env   # do not paste output externally
/var/www/mywave/venv/bin/python scripts/blog_raw_feed_smoke_check.py
curl -fsS https://mywavewake.ru/api/blog/diagnostics 2>/dev/null || echo "endpoint not deployed yet"
```

**Phase B — env verification (maintenance window, GM-approved):**

- Confirm `PARSER_NEWS_SPREADSHEET_ID=1RJpw2mAMej3a-VC6yKAsKkVQvzGStcjUC7LijNNyn50` and `PARSER_SHEET_NAME=raw_feed`.
- Ensure `PARSER_TAB` does not override to Admin spreadsheet.
- **No dedupe** of duplicate lines in same window unless GM explicitly approves.

**Phase C — code hardening (repo, deploy in separate window):**

- Serialize or retry `fetch_parser_news_rows()` under eventlet (lock or single-flight cache refresh).
- Ensure `/api/blog/diagnostics` (read-only counts, masked IDs) is deployed for ops.
- Document operator runbook: `docs/deployment/BLOG_CONTENT_VISIBILITY.md`.

### Test plan

| Step | Where |
|------|-------|
| `tests/unit/test_parser_news_sheet.py` | CI |
| `scripts/blog_raw_feed_smoke_check.py` | Staging/prod read-only |
| `GET /blog` shows ≥1 publishable card | Staging |
| `GET /api/blog/diagnostics` — sheets_count > 0 | Staging |
| Load test: 10 concurrent `/blog` requests, no tracebacks | Staging |
| After env fix: invalidate cache / TTL wait, re-check vitrine | Prod (approved window) |

### Production deploy required?

- **Env fix:** no code deploy; **yes** `.env` change (maintenance window).
- **Code hardening:** yes, git deploy to prod.

### Restart required?

- After **`.env` change:** yes, `mywave-site` only.
- After **code-only** deploy: yes, `mywave-site` only.
- Read-only diagnostics: **no**.

---

## SITE-BL-003 — Socket / invalid session logs

### Issue

Production logs contain non-fatal noise typical of **Gunicorn + eventlet + Flask-SocketIO**:

- `engineio.server` — invalid session / unknown session
- `OSError: [Errno 9] Bad file descriptor` on worker reload or client disconnect
- Duplicate log line `Server initialized for eventlet` (documented in `docs/CHAT_RUNTIME_AND_RELEASE.md`)

Chat HTTP path (`POST /chat/api`) remains primary; Socket.IO is auxiliary status/widget.

### Impact

| Area | Effect |
|------|-------|
| Booking / Phase 2 | **None** |
| Chat widget (HTTP) | **None** if `/chat/api` healthy |
| Log signal-to-noise | Degraded alerting |
| Socket.IO real-time status | Occasional reconnect for clients |

### Risk

| Risk | Level | Notes |
|------|-------|-------|
| Changing worker model away from eventlet | **High** | Breaks Socket.IO architecture |
| Ignoring true disconnect storms | Low | Could hide nginx timeout issues |
| Redis message queue misconfig | Medium | If `SOCKETIO_MESSAGE_QUEUE` set but Redis down |

### Proposed fix

**Phase A — classify (observe, read-only):**

```bash
journalctl -u mywave-site --since "24 hours ago" --no-pager \
  | grep -cE 'invalid session|Bad file descriptor' || true
curl -fsS https://mywavewake.ru/health
# confirm REDIS_URL / SOCKETIO_MESSAGE_QUEUE if present in .env (do not export)
```

**Phase B — config tuning (maintenance window):**

- Confirm `GUNICORN_WORKERS=1`, `worker_class=eventlet` per `docs/deployment/PRODUCTION_STACK.md`.
- Set `engineio` log level INFO/WARNING in prod (already partially in `app/__init__.py`).
- Verify Redis connectivity if `SOCKETIO_MESSAGE_QUEUE` is enabled.

**Phase C — code (P3, optional):**

- Single `socketio.init_app` in entrypoint to remove duplicate init log.
- Client-side: ensure reconnect backoff in socket client (already in `static/js/socket-status.js`).
- Add journald filter/alert threshold (e.g. >N invalid sessions/min) rather than zero tolerance.

### Test plan

| Step | Where |
|------|-------|
| `tests/e2e/test_chat_section_http.py` | CI |
| Manual: open site, idle 5 min, send chat message | Staging |
| Grep prod logs before/after log-level change | Prod |
| No increase in `/health` failures | Prod |

### Production deploy required?

**Optional.** Log-level tuning may be code or env. Not required for observe mode.

### Restart required?

**Yes**, if gunicorn config or env logging flags change. **No** for read-only log analysis.

---

## SITE-BL-004 — Post-release monitoring checklist

### Issue

After Phase 2 close, Site needs a **repeatable read-only** monitoring runbook (booking + health + blog smoke) without touching flags, `.env`, or sibling services.

Existing asset: `automation/production/prod_step4_verify_readonly.sh` (Step 4 era; still valid for core booking smoke).

### Impact

| Area | Effect |
|------|--------|
| Operational confidence | Faster detection of regressions |
| GM / TGbotAdmin coordination | Shared evidence format |
| Incident response | Baseline for “is prod healthy?” |

### Risk

| Risk | Level | Notes |
|------|-------|-------|
| Script accidentally mutates prod | Low if read-only enforced |
| False alarms from known blog/socket backlog | Medium | Document expected WARNs |

### Proposed fix

Add **`automation/production/prod_observe_monitoring.sh`** (read-only):

1. HEAD + Phase 2 flags (grep only, no write)
2. `systemctl is-active mywave-site`
3. `/health`, `/`, `/blog`, `/booking`
4. Boat/gym slots smoke (today + tomorrow)
5. Writer dry-run import check (Python, no calendar writes)
6. Optional WARN section: blog diagnostics, journald grep for Traceback / ImportError
7. Output to `/tmp/prod_observe_YYYYMMDD_HHMMSS.log`

Schedule: **manual or cron read-only** — only after GM approves automation on host.

### Test plan

| Step | Where |
|------|-------|
| Run script twice; identical flag section | Staging/prod read-only |
| Confirm no `.env` modification, no restart | Code review |
| Dry-run in CI with mocked curl | Optional |

### Production deploy required?

**No** for script usage via git pull on host. Script can live in repo first.

### Restart required?

**No.**

---

## SITE-BL-005 — Security hygiene plan (post-rollout exposure)

### Issue

During Phase 2 rollout, raw `.env` fragments, service tokens, and unsanitized logs appeared in operator sessions and evidence bundles. GM requires a **rotation plan** without executing rotation during observe mode.

### Impact

| Area | Effect |
|------|--------|
| Credential reuse | Compromise of Google, Telegram, OpenAI, Flask secret |
| Compliance / trust | Leaked logs in chat/email |
| Incident scope | Unclear without inventory |

### Risk

| Risk | Level | Notes |
|------|-------|-------|
| Rotating prod secrets during observe mode | **High** | Could break booking/chat mid-observe |
| Not rotating after confirmed exposure | **High** | Prolonged exposure window |
| Committing secrets to git | Critical | Must remain blocked |

### Proposed fix — inventory (document only, no rotation yet)

| Secret / material | Likely exposure surface | Rotation owner | Rotate in observe? |
|-------------------|-------------------------|----------------|--------------------|
| `SECRET_KEY` | `.env` in SSH output | Site + GM | **No** — needs session invalidation plan |
| `GOOGLE_SERVICE_ACCOUNT` JSON | server path, logs | Site | **No** — separate window |
| Google OAuth / API keys (if any) | `.env` | Site | **No** |
| `OPENAI_API_KEY` | `.env` | Site | **No** |
| `TELEGRAM_BOT_TOKEN` / alert tokens | `.env`, rollout logs | TGbotAdmin / Site | **No** |
| `MEDIA_UPLOAD_TOKEN` / cache invalidate tokens | `.env` | Site | **No** |
| Spreadsheet/Calendar IDs | logs | Low sensitivity | No rotation (IDs are not secrets) |
| Raw evidence files under `/tmp`, `/var/backups/mywave/` | server disk | Ops | Secure permissions only |

**Git hygiene (read-only verify now):**

```bash
# Local/repo CI — no prod change
git check-ignore -v .env
git log --all --full-history -- .env .env.production  # expect empty
grep -r "BEGIN PRIVATE KEY" --include="*.py" --include="*.json" .  # expect none in tracked files
```

**Future sanitized reporting template:**

- Replace token values with `[REDACTED]`
- Log only first 8 chars of spreadsheet ID
- Reference evidence by **path + timestamp**, not contents
- Closeout/backlog docs only

### Rotation execution plan (GM maintenance window — not observe mode)

1. GM approves **Security Maintenance Window** (off-peak).
2. Rotate in order: OpenAI → Google SA (re-issue JSON, deploy file) → Telegram tokens → Flask `SECRET_KEY` last (forces re-login).
3. Restart **`mywave-site` only** after Site secrets; coordinate TGbotAdmin for bot tokens.
4. Smoke: `/health`, one read-only booking slot check, one chat message on staging then prod.
5. Archive old evidence logs with restricted permissions; do not copy off-server.

### Test plan

| Step | Where |
|------|-------|
| `git check-ignore .env` passes | Repo |
| Secret scan in CI (gitleaks/trufflehog optional) | CI |
| Post-rotation smoke checklist (BL-004) | Prod window |
| Verify old token rejected (API 401) | After rotation |

### Production deploy required?

**No** for plan/inventory. **Yes** for rotation window (new `.env` / SA file on server).

### Restart required?

**Yes** after secret rotation — `mywave-site`; Telegram bot restart per TGbotAdmin scope (not during observe).

---

## Recommended execution order

```text
1. SITE-BL-004  — deploy read-only monitoring script (repo only, no prod change)
2. SITE-BL-005  — complete secret inventory + GM approve rotation window (plan only now)
3. SITE-BL-002  — read-only diagnostics → env fix window → optional code hardening
4. SITE-BL-001  — migration repair + DB fallback restore
5. SITE-BL-003  — log tuning / socket cleanup (lowest urgency)
```

---

## Observe mode guardrails (unchanged)

Do **not** until GM opens a scoped window:

- change `.env`, Phase 2 flags, Calendar/Sheet IDs
- restart `mywave-node`, `mywave-telegram-bot`
- modify `/opt/mywave-bot`
- run bundle rollout, production test bookings, `.env` dedupe
- rotate production secrets

---

## GM approval checklist (per backlog item)

| Item | GM approve | TGbotAdmin notify |
|------|------------|-------------------|
| BL-001 DB repair | Required | No |
| BL-002 env ID fix | Required | No |
| BL-002 code deploy | Required | No |
| BL-003 socket/log | Optional | No |
| BL-004 monitoring cron | Required for cron | Optional |
| BL-005 rotation window | **Required** | Yes if bot tokens |

---

**Site statement:** Phase 2 booking rollout remains **CLOSED**. This document tracks **separate non-blocking backlog** only. No production changes are authorized by this plan alone.
