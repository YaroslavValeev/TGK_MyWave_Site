# Events PR-3 — Staging QA Evidence (final)

**Date:** 2026-06-14  
**GM approval:** staging deploy + QA (staging only); classification accepted 2026-06-14  
**develop HEAD (staging):** `f0a9a9d9`  
**Overall QA status:** **PARTIAL** — core UI PASS; mobile screenshots pending  
**Production launch:** **not approved**

---

## 1. GM evidence summary (Site fill)

```text
Staging bind (canonical for QA):  http://127.0.0.1:5002
Staging hostname (DNS):             https://staging.mywavewake.ru — N/A infra (not app blocker)
Branch/head:                        develop @ f0a9a9d9
Flags used:                         EVENTS_API_ENABLED=1, EVENTS_PUBLIC_UI_ENABLED=1,
                                    EVENTS_REVIEW_API_ENABLED=0, EVENTS_CLASSIFIER_ENABLED=0,
                                    PUBLIC_SITE_BASE_URL=https://mywavewake.ru,
                                    ENABLE_GOOGLE_SERVICES=1, GUNICORN_BIND=127.0.0.1:5002

QA status:                          PARTIAL (pending mobile screenshots only)
Core UI:                            PASS
Sitemap:                            PASS
Detail / 301 redirect:              PASS
needs_review public UI:             PASS
YAML fallback:                      PASS
Mobile screenshots:                 PENDING — paths below
/api/events production hardening:   DOCUMENTED — see EVENTS_PR3_API_PRODUCTION_HARDENING.md
Production touched:                 no
main unchanged:                     yes (df26212d)
```

---

## 2. Owner live staging results (2026-06-14)

**Host:** VPS `/var/www/mywave-staging`  
**Service:** `mywave-staging.service` — active  
**Validation base:** `STAGING_BASE_URL=http://127.0.0.1:5002`

| Check | Result | Notes |
|-------|--------|-------|
| Service active | PASS | Gunicorn eventlet on 5002 |
| `/health` | PASS | 200 |
| `/events` | PASS | 200, ~67399 bytes |
| `/sitemap.xml` | PASS | 200, ~7712 bytes |
| `/competitions` | PASS | 302 → `/events?type=competition` |
| List canonical | PASS | `rel="canonical"` present |
| List JSON-LD | PASS | `application/ld+json` present |
| Markup | PASS | `events-section`, `events-filters`, `event-card`, `mywavewake` |
| Detail `/events/1360` | PASS | 200 |
| Detail canonical | PASS | `https://mywavewake.ru/events/1360` |
| Detail JSON-LD | PASS | present |
| Slug mismatch redirect | PASS | `/events/wrong-prefix-1360` → **301** → `/events/1360` |
| Unknown slug | PASS | 404 |
| HTML safety | PASS | no `source_url` / `raw_content` leak |
| Fresh critical errors | PASS | none in journalctl window |
| YAML fallback (flags OFF) | PASS | list 200 YAML; detail/competitions/api 404/503; restored |
| Review-queue disabled | PASS | `/api/events/review-queue` → **503** |
| needs_review on public UI | PASS | not in `/events` HTML; detail 404 for review rows |
| Automated script (localhost) | PASS* | PASS=7 FAIL=0 PARTIAL=3; manual grep overrides script false positives |

\* Script fix v2 (temp-file grep) pending push after `f0a9a9d9`; not blocking GM core acceptance.

---

## 3. `/api/events` boundary (GM accepted)

| Surface | Role | needs_review |
|---------|------|--------------|
| `GET /api/events` | Events-2 internal read-only diagnostic API | **May appear** without `?track_status=` filter — by design |
| `GET /events`, `GET /events/<slug>` | Events-3 public vitrine | **Never** — `is_public_eligible()` gate |
| `GET /api/events/review-queue` | Operator queue | **503** when `EVENTS_REVIEW_API_ENABLED=0` |

**Not an Events-3 staging failure.** Pre-production hardening required before prod discussion: see `EVENTS_PR3_API_PRODUCTION_HARDENING.md`.

---

## 4. Infra note — external staging URL

```text
curl https://staging.mywavewake.ru/
→ Could not resolve host (from VPS and Site dev network)
```

**Classification:** N/A infra — nginx/DNS gap. QA performed on `127.0.0.1:5002`. Not classified as Events-3 app regression.

---

## 5. Mobile screenshots (remaining blocker)

**Status:** PENDING — Owner to attach before final sign-off → **PASS**.

| File | URL / action | Pass criteria |
|------|--------------|---------------|
| `events-list-mobile.png` | `/events` @ 375px | Single-column cards, readable dates |
| `events-filters-mobile.png` | `/events` → open «Фильтры» | `<details>` expands, tap targets OK |
| `events-detail-mobile.png` | `/events/1360` (or published slug) | Title, dates, canonical in head |
| `home-ticker-mobile.png` | `/` home ticker block | Links wrap; no broken `/events/...` |
| `events-competition-filter-mobile.png` | `/events?type=competition` | Filter works (optional) |
| `events-empty-mobile.png` | empty filter state | only if reproduced |

**Repo path:** `docs/integration/evidence/events-3-staging/`  
**Owner guide:** `docs/integration/evidence/events-3-staging/README.md`

After attach: update §1 `Mobile screenshots: attached` and set **QA status: PASS**.

---

## 6. Automated regression (local / CI)

```bash
python -m pytest tests/unit/test_events_public_eligibility.py \
  tests/unit/test_events_slug.py \
  tests/unit/test_events_public_routes.py \
  tests/unit/test_events_public_serializer.py \
  tests/unit/test_events_api.py \
  tests/unit/test_event_classifier.py -q
```

Result at Events-3 merge: **55+ passed** (unit scope).

---

## 7. Staging script (localhost on VPS)

```bash
export STAGING_BASE_URL="http://127.0.0.1:5002"
bash scripts/staging_events_qa.sh | tee /tmp/events3-staging-qa-v2.log
```

Owner log summary (2026-06-14): PASS=7 FAIL=0 PARTIAL=3; core routes confirmed PASS manually.

---

## 8. Rollback (staging — tested PASS)

```bash
# /var/www/mywave-staging/.env
EVENTS_PUBLIC_UI_ENABLED=0
EVENTS_API_ENABLED=0
sudo systemctl restart mywave-staging
```

Verified: `/events` 200 YAML mode; `/events/test-slug` 404; `/competitions` 404; `/api/events` 503. Flags restored after test.

**Rollback tested:** yes

---

## 9. Related docs

| Doc | Purpose |
|-----|---------|
| `EVENTS_PR3_STAGING_QA_PACKAGE.md` | Full QA checklist |
| `EVENTS_PR3_STAGING_OWNER_RUNBOOK.md` | Owner copy-paste commands |
| `EVENTS_PR3_STAGING_SERVICE_RECOVERY.md` | Service down recovery |
| `EVENTS_PR3_API_PRODUCTION_HARDENING.md` | Prod `/api/events` decision (required before prod) |
| `EVENTS_PR2_API_REVIEW_PACKAGE.md` | Events-2 API contract |

---

## 10. Sign-off gate

| Gate | Status |
|------|--------|
| Events-3 public UI staging core | **PASS** |
| Overall staging sign-off | **PARTIAL** (mobile screenshots) |
| Production launch | **BLOCKED** |
| `/api/events` prod hardening decision | **DOCUMENTED** (decision at prod window) |
