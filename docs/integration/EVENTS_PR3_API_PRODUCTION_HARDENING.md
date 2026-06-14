# Events PR-3 — `/api/events` production hardening (pre-prod decision)

**Status:** Decision required before any production Events window  
**Date:** 2026-06-14  
**GM:** classification accepted on staging; hardening must be explicit before prod discussion

---

## 1. Problem statement

Events-3 public UI **requires** `EVENTS_API_ENABLED=1` (dependency: `EVENTS_PUBLIC_UI_ENABLED=1` → API ON).

When API is enabled, **`GET /api/events`** is reachable without authentication and, by Events-2 contract, may return rows with `track_status=needs_review` and `needs_review=true` unless the client passes `?track_status=published`.

Public vitrine routes (`/events`, `/events/<slug>`) use **`is_public_eligible()`** and never expose those rows. The gap is **exposure via JSON API**, not HTML.

---

## 2. Staging acceptance (2026-06-14)

On staging with approved flags:

| Check | Result |
|-------|--------|
| Public `/events` hides needs_review | PASS |
| Public detail 404 for review rows | PASS |
| `/api/events/review-queue` with `EVENTS_REVIEW_API_ENABLED=0` | 503 PASS |
| `/api/events` lists needs_review without filter | **By design** (Events-2 diagnostic) |
| Serializer: no raw_content, source_url, PII | PASS (allowlist) |

**Conclusion:** Staging QA does **not** require changing `/api/events` behavior. Production **does** require an explicit choice below.

---

## 3. Options (pick one before prod — GM decision)

### Option A — Auth/token on `/api/events*` (recommended)

- Gate all Events-2 routes with shared secret header or internal network only.
- Public users never call JSON API; SSR uses `get_public_items()` in-process (no HTTP self-fetch).
- **Pros:** Clearest boundary; review-queue can stay OFF on prod until operator tooling needs it.
- **Cons:** Small implementation PR (middleware or decorator on `events_api_bp`).

### Option B — Default `track_status=published` on prod `/api/events`

- Change `list_items()` default filter when `ENV=production` or new flag `EVENTS_API_PUBLISHED_ONLY=1`.
- **Pros:** Minimal surface if something still calls `/api/events` anonymously.
- **Cons:** Breaks operator diagnostic use without explicit `?track_status=needs_review`; must document.

### Option C — Keep `EVENTS_API_ENABLED=0` on prod until separate GM window

- **Conflict:** Events-3 public UI requires `EVENTS_API_ENABLED=1`.
- **Only valid if:** prod deploy keeps `EVENTS_PUBLIC_UI_ENABLED=0` (YAML-only vitrine) until Option A or B is implemented.
- **Pros:** Zero API exposure on prod short term.
- **Cons:** Delays Events-3 public UI on production.

---

## 4. Site recommendation

**For production Events-3 launch:** implement **Option A** (token or IP allowlist on `/api/events*`) in a small pre-prod PR; keep `EVENTS_REVIEW_API_ENABLED=0` on prod until operator workflow is approved.

**For staging:** current behavior remains acceptable (GM accepted 2026-06-14).

---

## 5. Implementation checklist (when GM approves prod window)

- [ ] GM selects Option A, B, or C (or hybrid: A + published default).
- [ ] PR to `develop`: hardening only; no parser/blog changes.
- [ ] Unit tests: anonymous `/api/events` → 401/403 (A) or published-only (B).
- [ ] Staging re-QA: public UI unchanged; API boundary verified.
- [ ] Update prod `.env` runbook — **never** enable flags on prod without this doc signed off.
- [ ] Evidence row in prod release package.

---

## 6. References

- Events-2 API contract: `EVENTS_PR2_API_REVIEW_PACKAGE.md` §5
- Public eligibility: `app/services/events/public_eligibility.py`
- API routes: `app/routes/events_api.py`
- Staging evidence: `EVENTS_PR3_STAGING_QA_EVIDENCE.md`
