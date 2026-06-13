# Events PR-2 — API + Review Layer (Implementation Package)

**Status:** Draft — pre-code, GM review required before implementation  
**Date:** 2026-06-13  
**Base branch:** `develop` (after Events-1 merge `caadc2af`)  
**Depends on:** Events-1 (`app/services/events/classifier.py`, `schema.py`)

**Production:** no deploy, no merge to `main`, `EVENTS_CLASSIFIER_ENABLED` remains OFF until GM approves wiring.

---

## 1. Goal

Expose classified events/competitions content via **read-only internal API** and a **review queue model** for `needs_review` rows — without public `/events` UI, without blog publishability changes, without parser/cron changes.

---

## 2. Proposed PR split

| PR | Scope |
|----|--------|
| **Events-2a** | Service layer: load + classify rows from Sheets, in-memory cache, review queue helpers |
| **Events-2b** | Routes: `GET /api/events`, diagnostics; token-gated review status update (optional) |

Single PR **Events-2** is acceptable if kept under ~500 LOC; prefer one PR for review simplicity.

---

## 3. Affected files (planned)

| File | Action |
|------|--------|
| `app/services/events/loader.py` | **new** — fetch raw_feed + competitions_ticker, classify, normalize |
| `app/services/events/review_queue.py` | **new** — filter/sort `needs_review`, manual override merge |
| `app/services/events/store.py` | **new** — cache, list/get by id |
| `app/routes/events_api.py` | **new** — blueprint, read-only endpoints |
| `app/config/events_features.py` | extend — `EVENTS_API_ENABLED` (default OFF) |
| `app/__init__.py` | register blueprint **only if** `EVENTS_API_ENABLED=1` |
| `tests/unit/test_events_loader.py` | **new** |
| `tests/unit/test_events_api.py` | **new** |
| `docs/integration/EVENTS_PR2_API_REVIEW.md` | evidence doc |

**Not touched:** `app/services/blog/store.py`, parser cron, public templates, `competitions` ticker behavior.

---

## 4. Feature flags (default OFF)

```text
EVENTS_CLASSIFIER_ENABLED=0   # existing Events-1
EVENTS_API_ENABLED=0          # new — gates blueprint + /api/events/*
EVENTS_REVIEW_API_ENABLED=0   # new — gates review status override endpoints
```

API routes return **404** or **503** when flags OFF (consistent with Social-1 pattern).

---

## 5. API design (read-only)

### `GET /api/events`

Query params:

| Param | Type | Notes |
|-------|------|-------|
| `content_type` | enum | `event,competition,camp,workshop,news` |
| `track_status` | enum | incl. `needs_review`, `published`, `parsed` |
| `city` | string | partial match |
| `from_date` | YYYY-MM-DD | start_date >= |
| `to_date` | YYYY-MM-DD | start_date <= |
| `limit` | int | default 50, max 100 |
| `offset` | int | pagination |
| `source` | enum | `raw_feed`, `competitions_ticker`, `all` |

Response (public-safe fields only):

```json
{
  "items": [
    {
      "event_id": "...",
      "content_type": "competition",
      "title": "...",
      "start_date": "2026-08-01",
      "end_date": "2026-08-03",
      "city": "Orlando",
      "track_status": "needs_review",
      "needs_review": true,
      "source_hint": "competitions_ticker"
    }
  ],
  "count": 1,
  "filters_applied": {},
  "classifier_enabled": false
}
```

**No PII, no full_description, no source_url in list** (detail endpoint optional in Events-2 if GM approves).

### `GET /api/events/review-queue`

Same as above with `track_status=needs_review` preset; sorted by `confidence ASC`, then `created_at`.

### `GET /api/events/diagnostics`

Read-only counts: by `content_type`, by `track_status`, `needs_review_count`, cache age, spreadsheet_id_tail (masked).

### Optional (GM approval required for Events-2):

`POST /api/events/review/{event_id}/override` — token-gated manual `content_type` / `track_status` override stored **in-memory or separate Sheet tab** — **defer to Events-2b** if scope too large.

---

## 6. Review queue model

| Field | Source |
|-------|--------|
| `event_id` | row id |
| `classification` | Events-1 `ClassificationResult` |
| `normalized` | `NormalizedContentItem` |
| `review_reasons` | `classification.reasons` |
| `manual_override` | optional dict (Events-2b) |

Rules:

- Rows with `needs_review=true` **never** appear as `published` in API unless manual override (future).
- Classifier re-run on cache refresh; no writeback to Parser News in Events-2.
- Blog vitrine **unchanged** — `should_route_to_blog_vitrine()` not wired.

---

## 7. Data sources (read-only)

| Source | Loader |
|--------|--------|
| `raw_feed` | `fetch_parser_news_rows()` + `classify_row()` |
| `competitions_ticker` | existing store pattern + `classify_competitions_ticker_row()` |

Cache TTL: reuse `COMPETITIONS_SHEETS_CACHE_TTL` or new `EVENTS_SHEETS_CACHE_TTL=300` (config only, default OFF path uses mock in tests).

---

## 8. Not in scope (Events-2)

- Public `/events`, `/events/<slug>`, `/competitions`
- Blog store / publishability changes
- Parser Bot / cron changes
- Autopublish
- Production deploy / merge to `main`
- `.env` prod changes
- Write to Sheets (except optional deferred override tab)

---

## 9. Test plan

```bash
python -m pytest tests/unit/test_events_loader.py tests/unit/test_events_api.py tests/unit/test_event_classifier.py -q
```

| Case | Expect |
|------|--------|
| Flags OFF | `/api/events` → 404 or 503 |
| Flags ON (test config) | list returns classified items |
| Filter `content_type=competition` | only competitions |
| Filter `track_status=needs_review` | review queue |
| Missing date competition row | in review queue |
| Public response | no `parent_*`, no health, no full body |
| Blog regression | existing blog tests unchanged |

---

## 10. Rollout (develop only)

1. Merge Events-2 to `develop` only.
2. Staging: `EVENTS_API_ENABLED=1` for QA (not prod).
3. Prod: flags remain OFF until Events-3+ GM window.

---

## 11. Risks

| Risk | Mitigation |
|------|------------|
| Accidental merge to `main` triggers deploy | PR base = `develop` only |
| API exposes PII from raw_feed | Public-safe serializer; field allowlist |
| Performance (double Sheets read) | Shared cache with competitions/blog where safe |
| Scope creep into UI | Explicit not-in-scope list; separate Events-3 PR |

---

## 12. GM approval checklist (before coding)

- [ ] Approve API surface (`GET /api/events`, diagnostics, review-queue)
- [ ] Approve new flags `EVENTS_API_ENABLED`, `EVENTS_REVIEW_API_ENABLED`
- [ ] Confirm defer manual override POST to Events-2b or later
- [ ] Confirm no blog wiring in Events-2

---

**Site statement:** Events-2 package is planning-only. Implementation starts after GM approval of this document.
