# Events PR-3 — Public UI (Evidence)

**GM approval:** Events-3 implementation  
**Base:** `develop` (`16ef046c`)  
**Branch:** `events-3-public-ui`  
**Target PR:** `develop` (NOT `main`)

---

## GM evidence checklist

| Field | Value |
|-------|-------|
| Branch | `events-3-public-ui` |
| Commit | _(after push)_ |
| PR title/link | _(after PR create)_ |
| Target branch | `develop` |
| Flags default OFF | `EVENTS_PUBLIC_UI_ENABLED=0` |
| Canonical domain | `https://mywavewake.ru` |
| No parser/cron | Yes |
| No blog publishability | Yes |
| No production changes | Yes |
| PR target develop | Yes |

---

## Routes added/changed

| Route | Behavior |
|-------|----------|
| `GET /events` | Flag OFF → YAML unchanged; Flag ON → public-eligible store |
| `GET /events/<slug>` | Flag OFF → 404; Flag ON + API → detail; API OFF → 503 |
| `GET /competitions` | Flag OFF → 404; Flag ON → **302** → `/events?type=competition` |

---

## Slug strategy

- Format: `{title-slug}-{event_id_tail}`
- Lookup by `event_id_tail`; title mismatch → **301** to canonical slug
- Collision prevented by unique `event_id_tail`

---

## Public eligibility

- `is_public_eligible()` in `public_eligibility.py`
- `needs_review` never in public list/detail
- Requires `track_status=published`, title, dates for event types

---

## YAML fallback

- Flag OFF: existing YAML path
- Flag ON + empty store / load error / API OFF: YAML fallback, no 500

---

## Ticker links

- `enrich_competitions_ticker()` — internal `/events/<slug>` only when public-eligible
- Otherwise keeps external `href`

---

## SEO / canonical

- `PUBLIC_SITE_BASE_URL` default `https://mywavewake.ru`
- JSON-LD Event on dynamic pages; sitemap includes `/events` + slugs when flag ON

---

## Tests

```bash
python -m pytest tests/unit/test_events_public_eligibility.py tests/unit/test_events_slug.py tests/unit/test_events_public_routes.py tests/unit/test_events_public_serializer.py tests/unit/test_events_api.py tests/unit/test_event_classifier.py -q
```

Result: **62 passed** (incl. features + jsonld regression)

---

## Affected files

- `app/config/events_features.py`
- `app/routes/events_public.py`
- `app/services/events/public_eligibility.py`
- `app/services/events/slug.py`
- `app/services/events/public_urls.py`
- `app/services/events/public_serializer.py`
- `app/services/events/ticker_links.py`
- `app/services/events/store.py`
- `app/__init__.py`
- `templates/events.html`, `events_detail.html`
- `templates/partials/home_competitions_ticker.html`
- `templates/sitemap.xml`
- `env.example`, `tests/conftest.py`
- `tests/unit/test_events_public_*.py`, `test_events_slug.py`
- `tests/unit/test_events_features.py`, `tests/test_events_jsonld.py`
