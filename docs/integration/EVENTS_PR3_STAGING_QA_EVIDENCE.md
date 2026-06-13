# Events PR-3 — Staging QA Evidence

**Date:** 2026-06-13  
**GM approval:** staging deploy + QA (staging only)  
**develop HEAD:** `eb2ab0ca`  
**Status:** **PENDING LIVE QA** — blocked from Site dev workstation (see §2)

---

## 1. GM evidence template (fill after Owner runs staging)

```text
Staging URL:              https://staging.mywavewake.ru
Branch/head:              develop @ eb2ab0ca (target)
Flags used:               EVENTS_API_ENABLED=1, EVENTS_PUBLIC_UI_ENABLED=1,
                          EVENTS_REVIEW_API_ENABLED=0, EVENTS_CLASSIFIER_ENABLED=0,
                          PUBLIC_SITE_BASE_URL=https://mywavewake.ru, ENABLE_GOOGLE_SERVICES=1

QA status:                PENDING / PARTIAL / PASS / FAIL

/events dynamic:          _TBD_
/events YAML fallback:    _TBD_
/events/<slug>:           _TBD_
slug canonical redirect:  _TBD_
/competitions 302:        _TBD_
needs_review hidden:      _TBD_
empty/error fallback:     _TBD_
ticker links:             _TBD_
mobile screenshots:       docs/integration/evidence/events-3-staging/ (attach)
SEO/canonical:            _TBD_
JSON-LD:                  _TBD_
Sitemap:                  _TBD_
Logs/errors:              _TBD_
Rollback tested:          _TBD_
Production touched:       no
main unchanged:           yes (df26212d)
```

---

## 2. Blocker from Site dev environment (2026-06-13)

Live staging QA from Cursor/dev workstation **not completed**:

```text
curl https://staging.mywavewake.ru/
→ Could not resolve host: staging.mywavewake.ru
```

**Interpretation:** staging hostname is not public-DNS reachable from this network (internal/VPN/SSH-tunnel only per `BOOKING_PHASE2_STAGING_E2E_PACKAGE.md`).

**Production:** not touched. `main` = `df26212d`. Deploy workflow (`push → main`) not triggered.

---

## 3. Automated regression (local / CI — completed)

```bash
python -m pytest tests/unit/test_events_public_eligibility.py \
  tests/unit/test_events_slug.py \
  tests/unit/test_events_public_routes.py \
  tests/unit/test_events_public_serializer.py \
  tests/unit/test_events_api.py \
  tests/unit/test_event_classifier.py -q
```

Result: **55 passed** (Events-3 unit scope; develop @ eb2ab0ca)

Maps to staging checks:

| Check | Unit coverage |
|-------|----------------|
| needs_review hidden | `test_needs_review_*` |
| slug / 301 | `test_slug_mismatch_redirect` |
| /competitions 302 | `test_competitions_redirect_302` |
| YAML fallback / no 500 | `test_public_ui_on_api_off_no_500`, `test_load_error_fallback` |
| ticker links | `TestTickerLinks` |
| public serializer safety | `test_*_safe`, JSON-LD domain |

---

## 4. Owner staging deploy (approved — run on VPS)

```bash
cd /var/www/mywave-staging
sudo -u www-data git fetch origin develop
sudo -u www-data git checkout develop
sudo -u www-data git pull --ff-only origin develop
git rev-parse HEAD   # expect eb2ab0ca or newer on develop

# Edit ONLY /var/www/mywave-staging/.env — add flags (§5)
sudo systemctl restart mywave-staging
# DO NOT: systemctl restart mywave-site | mywave-node | mywave-telegram-bot
```

---

## 5. Staging flags (approved)

```text
EVENTS_API_ENABLED=1
EVENTS_PUBLIC_UI_ENABLED=1
EVENTS_REVIEW_API_ENABLED=0
EVENTS_CLASSIFIER_ENABLED=0
PUBLIC_SITE_BASE_URL=https://mywavewake.ru
ENABLE_GOOGLE_SERVICES=1
```

---

## 6. Automated staging script (on host or tunnel)

```bash
export STAGING_BASE_URL="https://staging.mywavewake.ru"
# or: export STAGING_BASE_URL="http://127.0.0.1:5002"  # SSH tunnel
bash scripts/staging_events_qa.sh
```

---

## 7. Manual QA (required — cannot skip)

| ID | Action | Pass criteria |
|----|--------|---------------|
| M1 | `/events` flags ON | Dynamic cards from Sheets; filters work |
| M2 | Flags OFF + restart | YAML `/events` unchanged |
| M3 | Published slug detail | 200, canonical, JSON-LD |
| M4 | needs_review row | Absent on list; detail 404 |
| M5 | Home ticker | Internal `/events/...` only when eligible |
| M6 | Mobile 375px | Screenshots in `docs/integration/evidence/events-3-staging/` |
| M7 | Rollback | Flags OFF → YAML, detail 404 |

---

## 8. Rollback (staging)

```bash
# /var/www/mywave-staging/.env
EVENTS_PUBLIC_UI_ENABLED=0
EVENTS_API_ENABLED=0
sudo systemctl restart mywave-staging
```

---

## 9. Related docs

- Package: `EVENTS_PR3_STAGING_QA_PACKAGE.md`
- Bootstrap: `BOOKING_PHASE2_STAGING_BOOTSTRAP_RUNBOOK.md`
