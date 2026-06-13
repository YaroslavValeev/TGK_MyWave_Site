# Events PR-3 — Staging / QA Validation Package

**Status:** Ready for staging QA (post-merge PR #24)  
**Date:** 2026-06-13  
**develop HEAD:** `27868d10` (Events-3 merge)  
**Production:** **no deploy**, **no flags ON on prod**

---

## 1. Scope

Validate Events-3 public UI on **staging only** before any production window:

- `/events` vitrine
- `/events/<slug>` detail
- `/competitions` → 302 redirect
- `needs_review` exclusion
- YAML fallback
- ticker links
- SEO / canonical / sitemap
- mobile layout smoke

**Out of scope for this QA:** parser/cron, blog wiring, prod deploy, merge to `main`.

---

## 2. Staging flags (enable on staging only)

Add to **staging `.env`** (never production without GM window):

```text
# Events track — staging QA window only
EVENTS_API_ENABLED=1
EVENTS_PUBLIC_UI_ENABLED=1
EVENTS_REVIEW_API_ENABLED=0          # optional: 1 only for internal review-queue QA
EVENTS_CLASSIFIER_ENABLED=0          # unchanged; loader works without this flag
PUBLIC_SITE_BASE_URL=https://mywavewake.ru
EVENTS_SHEETS_CACHE_TTL=300
```

**Dependency rule (enforced in code):**

```text
EVENTS_PUBLIC_UI_ENABLED=1  requires  EVENTS_API_ENABLED=1
```

**Prerequisites on staging:**

- `PARSER_NEWS_SPREADSHEET_ID` / sheet access configured (same as blog/competitions ticker)
- `ENABLE_GOOGLE_SERVICES=1` if staging reads Sheets live (match staging blog setup)
- Restart `mywave-staging` after `.env` change (staging only, GM-approved)

**Verify flags OFF by default in repo:**

```bash
python -c "from app.config.events_features import get_events_feature_flags; print(get_events_feature_flags())"
# EVENTS_PUBLIC_UI_ENABLED: False, EVENTS_API_ENABLED: False (without env override)
```

---

## 3. QA checklist — `/events`

| # | Check | Pass criteria |
|---|--------|---------------|
| E3-L01 | Flag OFF baseline | With flags OFF: page loads 200, YAML cards unchanged vs pre-Events-3 |
| E3-L02 | Flag ON list | Published competitions/events from Sheets appear as cards |
| E3-L03 | needs_review hidden | Rows with missing date / low confidence **not** in list |
| E3-L04 | Filter `?type=competition` | Only competitions shown |
| E3-L05 | Filter `?city=...` | City partial match works |
| E3-L06 | Empty filter | “Нет мероприятий по фильтру” + reset link |
| E3-L07 | Empty store | YAML fallback banner, no 500 |
| E3-L08 | API OFF fallback | `PUBLIC_UI=1`, `API=0`: list falls back to YAML, no 500 |
| E3-L09 | Load error | Simulate Sheets failure → friendly page, no stack trace |
| E3-L10 | Public-safe HTML | View source: no `source_url`, `raw_content`, tokens |
| E3-L11 | Mobile filters | `<details>` filters usable on narrow viewport |

**Manual URLs (staging):**

```text
/events
/events?type=competition
/events?type=camp&city=Сочи
```

---

## 4. QA checklist — `/events/<slug>`

| # | Check | Pass criteria |
|---|--------|---------------|
| E3-D01 | Published detail 200 | Valid slug opens detail with title, dates, location |
| E3-D02 | needs_review 404 | Detail URL for review row returns **404** |
| E3-D03 | Flag OFF 404 | `/events/any-slug` → 404 when `EVENTS_PUBLIC_UI_ENABLED=0` |
| E3-D04 | Slug mismatch 301 | Old title slug + correct `event_id_tail` → 301 to canonical |
| E3-D05 | Unknown slug 404 | Random slug → 404 |
| E3-D06 | Canonical meta | `<link rel="canonical" href="https://mywavewake.ru/events/...">` |
| E3-D07 | JSON-LD Event | `application/ld+json` with `startDate`, `location` |
| E3-D08 | No raw leak | No source body / PII in HTML |

**Slug format:** `{title-slug}-{event_id_tail}`

---

## 5. QA checklist — `/competitions`

| # | Check | Pass criteria |
|---|--------|---------------|
| E3-C01 | Flag OFF | `/competitions` → **404** |
| E3-C02 | Flag ON redirect | **302** → `/events?type=competition` |
| E3-C03 | Location header | `Location` contains `type=competition` |
| E3-C04 | Final page | After follow redirect: competition filter applied |

```bash
curl -I https://<staging-host>/competitions
# Expect: HTTP/1.1 302, Location: .../events?type=competition
```

**Note:** **301** only after separate GM prod launch approval.

---

## 6. needs_review — negative test

**Goal:** confirm `needs_review` never appears on public surfaces.

| Step | Action | Expected |
|------|--------|----------|
| 1 | Identify a ticker/raw row classified `needs_review` (missing date or title) | Visible in `GET /api/events/review-queue` when `EVENTS_REVIEW_API_ENABLED=1` |
| 2 | Open `/events` | Row **absent** |
| 3 | Attempt `/events/<slug>` for that row | **404** |
| 4 | View page source / JSON-LD | No title/body from review row |

**Automated regression (local/CI):**

```bash
python -m pytest tests/unit/test_events_public_eligibility.py tests/unit/test_events_public_routes.py -q -k "needs_review"
```

---

## 7. YAML fallback test

| Scenario | Setup | Expected |
|----------|--------|----------|
| Empty store | No published rows in Sheets | YAML showcase cards OR empty-state modal; **no 500** |
| Sheets down | Break spreadsheet id temporarily on staging | Fallback message / YAML; **no 500** |
| API OFF | `EVENTS_PUBLIC_UI_ENABLED=1`, `EVENTS_API_ENABLED=0` | YAML path on `/events`; detail **503** |

Verify copy: “Показываем резервное расписание…” when `yaml_fallback` active.

---

## 8. Mobile screenshots checklist

Capture on staging (375px and 390px width):

| Screen | File name (suggested) | Verify |
|--------|------------------------|--------|
| `/events` list | `events-list-mobile.png` | Single-column cards, readable dates |
| `/events` filters open | `events-filters-mobile.png` | `<details>` expands, tap targets ≥44px |
| `/events/<slug>` detail | `events-detail-mobile.png` | Title, dates, back link |
| Home ticker | `home-ticker-mobile.png` | Links wrap; internal links no forced `_blank` |
| Empty state | `events-empty-mobile.png` | Modal or message readable |

Store under `docs/integration/evidence/events-3-staging/` (optional, GM review).

---

## 9. SEO / canonical / sitemap

| # | Check | Pass criteria |
|---|--------|---------------|
| E3-S01 | List canonical | `https://mywavewake.ru/events` (not mywavetreaning.ru) |
| E3-S02 | Detail canonical | Per-slug canonical on detail page |
| E3-S03 | JSON-LD | Valid Event objects; `startDate` ISO format |
| E3-S04 | Sitemap | `/sitemap.xml` includes `/events` when flag ON |
| E3-S05 | Detail slugs in sitemap | Published slugs listed under `/events/{slug}` |
| E3-S06 | `/competitions` not indexed | 302 only; no duplicate catalog URL |

**Tools (optional):**

- View source → canonical link
- `curl https://<staging>/sitemap.xml | grep events`

---

## 10. Ticker link check

| # | Check | Pass criteria |
|---|--------|---------------|
| E3-T01 | Flag OFF | Ticker unchanged (external links, `_blank`) |
| E3-T02 | Public item | Ticker link → `/events/{slug}` (same tab) |
| E3-T03 | Non-public item | Keeps external `event_url` / `source_url` |
| E3-T04 | No broken slugs | No 404 links from home ticker for visible items |
| E3-T05 | Unknown id | External href preserved |

---

## 11. Rollback plan (flags OFF)

If staging QA fails or regression detected:

```text
1. Set EVENTS_PUBLIC_UI_ENABLED=0
2. Set EVENTS_API_ENABLED=0
3. Restart staging app service
4. Verify:
   - /events → YAML-only (pre-Events-3 behavior)
   - /events/<slug> → 404
   - /competitions → 404
   - Home ticker → legacy external links
   - /sitemap.xml → no dynamic event slugs
```

**No code rollback required** — flags gate all Events-3 behavior.

**Production:** keep all `EVENTS_*=0` until dedicated GM deploy window.

---

## 12. Sign-off template

```text
Staging host:
QA date:
Flags used: EVENTS_API_ENABLED=1, EVENTS_PUBLIC_UI_ENABLED=1
/events list: pass/fail
/events detail: pass/fail
/competitions redirect: pass/fail
needs_review negative: pass/fail
YAML fallback: pass/fail
Mobile smoke: pass/fail
SEO/sitemap: pass/fail
Ticker links: pass/fail
Blockers:
Ready for prod discussion: yes/no (GM only)
```

---

## 13. Related docs

- Package: `docs/integration/EVENTS_PR3_PUBLIC_UI_PACKAGE.md`
- Evidence: `docs/integration/EVENTS_PR3_PUBLIC_UI.md`
- Events-2 API: `docs/integration/EVENTS_PR2_API_REVIEW.md`
- Audit: `docs/integration/EVENTS_COMPETITIONS_PARSER_DISPLAY_AUDIT.md`
