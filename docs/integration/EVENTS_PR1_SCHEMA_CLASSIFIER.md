# Events PR-1 — Schema + Classifier

**GM approval:** `APPROVED: PR Events-1 — Schema + classifier`  
**Base branch:** `develop`  
**Feature branch:** `events-1-schema-classifier`  
**Production:** no deploy, no merge to `main`

---

## Summary

Events-1 adds a read-only classification layer for mixed content from Parser News Sheets:

- normalized DTO (`NormalizedContentItem`);
- `content_type`: `event | competition | camp | workshop | news`;
- `track_status` including `needs_review`;
- heuristics + explicit `content_type` column support;
- competitions_ticker adapter;
- unit tests;
- `EVENTS_CLASSIFIER_ENABLED=0` by default (not wired to blog UI yet).

**Not included:** public `/events`, parser/cron changes, autopublish, blog store integration.

---

## Affected files

| File | Role |
|------|------|
| `app/services/events/content_types.py` | Canonical enums / thresholds |
| `app/services/events/schema.py` | DTO + row normalizers |
| `app/services/events/classifier.py` | Classification logic |
| `app/services/events/__init__.py` | Public exports |
| `app/config/events_features.py` | `EVENTS_CLASSIFIER_ENABLED` (OFF) |
| `tests/unit/test_event_classifier.py` | Classifier tests |
| `tests/unit/test_events_features.py` | Flag tests |

---

## Schema summary

`NormalizedContentItem` fields (subset):

`event_id`, `source_id`, `source_type`, `source_url`, `content_type`, `title`, `short_description`, `sport_type`, `start_date`, `end_date`, `location_name`, `city`, `organizer_name`, `registration_url`, `price_label`, `track_status`, `media_status`, `source_media_url`, `classification`

Normalizers:

- `normalize_raw_feed_row()` — blog/parser rows
- `normalize_competitions_ticker_row()` — ticker rows

---

## Classifier rules

| Signal | Effect |
|--------|--------|
| Explicit `content_type` column | Highest priority (0.92 confidence) |
| Keywords: соревнование/турнир/championship/contest | `competition` |
| Keywords: лагерь/camp/кэмп | `camp` |
| Keywords: мастер-класс/workshop | `workshop` |
| Keywords: мероприятие/фестиваль | `event` |
| Keywords: новость/обзор/итог | `news` |
| `start_date` present | Boost competition/event/camp |
| `location`/`city` present | Boost competition/event |
| `source_type`/`source_name` federation tokens | Boost competition |
| No strong signal | Fallback `news` (low confidence) |

`competitions_ticker` rows → always `competition` (contract).

---

## `needs_review` behavior

Set when **any**:

- confidence &lt; 0.55;
- timed type (`competition/event/camp/workshop`) without `start_date`;
- weak competition signal;
- ticker row missing `event_name` or dates.

`track_status = needs_review` — **must not** auto-publish or join public vitrine.

Helper `should_route_to_blog_vitrine()` returns `False` for `needs_review` and non-`news` types (for Events-2 wiring; **not** connected in Events-1).

---

## Tests

```bash
python -m pytest tests/unit/test_event_classifier.py tests/unit/test_events_features.py -q
```

---

## Confirmations

| Item | Status |
|------|--------|
| No public UI | Yes |
| No parser/cron changes | Yes |
| No production changes | Yes |
| PR target `develop` | Yes |
| `EVENTS_CLASSIFIER_ENABLED` default OFF | Yes |
| Blog publishability unchanged | Yes (no store.py edits) |
