# Events PR-2 — API + Review Layer (Evidence)

**GM approval:** Events-2 read-only API  
**Base branch:** `develop` (`ad5aba41`)  
**Feature branch:** `events-2-api-review-layer`  
**Target PR:** `develop` (NOT `main`)  
**Production:** observe mode — no deploy

---

## GM evidence checklist

| Field | Value |
|-------|-------|
| Branch | `events-2-api-review-layer` |
| Commit | _(fill after commit)_ |
| PR title/link | _(fill after PR create)_ |
| Target branch | `develop` |
| Flags default OFF | Yes — `EVENTS_API_ENABLED=0`, `EVENTS_REVIEW_API_ENABLED=0` |
| No public UI | Yes |
| No blog/store wiring | Yes |
| No parser/cron changes | Yes |
| No production changes | Yes |
| main unchanged | Yes |
| PR target develop | Yes |
| POST override | Not included |

---

## Affected files

| File | Role |
|------|------|
| `app/services/events/loader.py` | Load + classify raw_feed / competitions_ticker rows |
| `app/services/events/store.py` | In-memory cache, filters, diagnostics |
| `app/services/events/review_queue.py` | `needs_review` queue sorted by confidence |
| `app/services/events/serializer.py` | Public-safe API payload allowlist |
| `app/routes/events_api.py` | Read-only blueprint routes |
| `app/config/events_features.py` | `EVENTS_API_ENABLED`, `EVENTS_REVIEW_API_ENABLED` |
| `app/__init__.py` | Register `events_api_bp` |
| `env.example` | Document new flags |
| `tests/conftest.py` | Force Events flags OFF in test suite |
| `tests/unit/test_events_loader.py` | Loader unit tests |
| `tests/unit/test_events_api.py` | API, flags OFF, serializer safety |
| `tests/unit/test_events_features.py` | Flag default + dependency tests |

---

## API routes added

| Route | Method | Flag gate |
|-------|--------|-----------|
| `/api/events` | GET | `EVENTS_API_ENABLED=1` |
| `/api/events/review-queue` | GET | `EVENTS_API_ENABLED=1` + `EVENTS_REVIEW_API_ENABLED=1` |
| `/api/events/diagnostics` | GET | `EVENTS_API_ENABLED=1` |

**Flags OFF:** all routes return **503** `events_api_disabled`.

**Query filters:** `content_type`, `track_status`, `city`, `from_date`, `to_date`, `limit`, `offset`, `source`.

**Not included:** `POST /api/events/review/{event_id}/override` (deferred to Events-2b/3).

---

## Serializer public-safe evidence

Allowlist in `serialize_api_item()`:

- `event_id`, `content_type`, `title`, `start_date`, `end_date`, `city`, `location_name`, `sport_type`, `track_status`, `needs_review`, `confidence`, `source_hint`

Excluded from API responses:

- raw body / `raw_content` / `text` / `final_posts`
- `source_url`, media URLs, organizer fields
- credentials, tokens, PII-like fields
- unsafe diagnostic dumps

Tests: `TestSerializer::test_serialize_api_item_safe`, `assert_api_payload_safe()` in API list test.

---

## Tests command / result

```bash
python -m pytest tests/unit/test_events_loader.py tests/unit/test_events_api.py tests/unit/test_event_classifier.py -q
```

Result: **25 passed**

---

## Scope confirmations

| Item | Status |
|------|--------|
| Service layer (loader, review_queue, store) | Done |
| Read-only routes | Done |
| Filters | Done |
| Feature flags default OFF | Done |
| Classifier regression | Events-1 tests pass |
| Public UI (`/events`, `/competitions`) | Not included |
| Blog/store wiring | Not included |
| Parser/cron / Parser Bot | Not included |
| Production deploy / merge to main | Not included |
