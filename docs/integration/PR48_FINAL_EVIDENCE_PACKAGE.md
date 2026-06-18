# PR #48 — Final evidence package (GM review)

**Status:** REVIEW ONLY — **Execution NOT STARTED**  
**PR:** https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/48  
**Release branch:** `release/prod-ui-jun2026`  
**Date:** 2026-06-18

---

## §6 Final package block

```text
Current prod HEAD:        ae4b6272 (PR45 hotfix; server unchanged since rollout)
Target release HEAD:      bd9f303b
origin/main HEAD:         0274a54e (PR45 + deploy.yml safety only)

Diff stat:                94 files, +123509 / −90
Diff name-only:           see manifest below (94 paths)
Events leakage check:     PASS (no events/classifier routes or events_features)
DB migration check:       PASS (no migrations/ changes)
Execution status:         NOT STARTED
```

---

## Diff name-only (94 files)

**App / config:**  
`app/__init__.py`, `app/config/social_features.py`, `app/routes/api.py`, `app/routes/brand.py`, `app/routes/services.py`, `app/routes/social.py`, `app/services/blog/publish.py`, `app/services/blog/store.py`, `app/services/brand/*`, `app/services/competitions/store.py`, `app/services/competitions/visibility.py`, `app/services/social_*.py`, `config.py`, `configs/services.yaml`, `env.example`

**Docs:**  
`docs/integration/BLOG_MEDIA_BACKFILL_RUNBOOK.md`, `PROD_UI_JUN2026_ROLLOUT_RUNBOOK.md`, `SOCIAL_MISSION_STAGING_UI_EVIDENCE.md`, `SOCIAL_PR1_DATA_LAYER.md`

**Static (code):**  
`static/css/branding.css`, `competitions-ticker.css`, `mobile-home.css`, `social-mission.css`, `static/js/competitions-ticker.js`, `social-application-form.js`

**Templates:**  
`templates/base.html`, `index.html`, `partials/brand_logo.html`, `home_competitions_ticker.html`, `legal_consent.html`, `social_*`, `social/index.html`

**Tests:**  
`tests/conftest.py`, `test_blog_media_regression.py`, `test_brand_logo_package.py`, `test_competitions_ticker.py`, `test_home_hero_logo.py`, `test_services_order.py`, `test_social_*.py`

**Logo package (binary-heavy):**  
`static/images/logotip_MyWave/MyWave_logo_package_brand_turquoise/**` (png, svg, pdf, eps, tif, jpg, webm, mov, mp4)

---

## Large static / binary files (added)

| Category | Count | Notes |
|----------|-------|--------|
| PNG/JPG/WebP | ~30 | Logo masters + previews |
| SVG | 6 | In-repo text |
| PDF/EPS/TIF | 8 | Print outdoor |
| Video (webm/mov/mp4) | 4 | Brand reveal assets (~8 MB mov) |
| EPS vector dumps | 2 | Large line-count in git stat |

**Runtime-critical assets:** turquoise SVG + PNG used by `brand_logo.html`; video files not required for homepage.

---

## Events leakage check

```bash
git diff ae4b6272..bd9f303b --name-only | grep -Ei 'events|classifier|events_features'
# Result: (empty) PASS
```

**Intentionally included (home ticker only):**  
`competitions/store.py`, `competitions/visibility.py`, `home_competitions_ticker.html`, `competitions-ticker.js/css`

**Excluded:** `app/config/events_features.py`, `app/routes/events*`, `templates/events*.html`

---

## DB migration check

```bash
git diff ae4b6272..bd9f303b --name-only -- migrations/
# Result: (empty) PASS — no flask db upgrade required for this rollout
```

---

## Flags final (after execution approval only)

```env
SOCIAL_MODULE_ENABLED=1
SOCIAL_WIDGET_ENABLED=1
SOCIAL_APPLICATIONS_ENABLED=1
SOCIAL_PUBLIC_STATS_ENABLED=0
SOCIAL_ADMIN_NOTIFICATIONS_ENABLED=0

EVENTS_CLASSIFIER_ENABLED=0
EVENTS_API_ENABLED=0
EVENTS_PUBLIC_UI_ENABLED=0
```

Apply **after** merge + restart; backup `.env` first.

---

## Blocker 5.1 — Hero logo visual sign-off

**Staging base URL:** Owner tunnel / staging host (develop `6fcf7884` area)

| Check | Owner evidence |
|-------|----------------|
| Desktop hero logo fully visible | Screenshot `/` — **PENDING** |
| Mobile hero logo not clipped | Screenshot `/` 375px — **PENDING** |
| Header logo unchanged (turquoise brand) | Screenshot header — **PENDING** |
| Footer logo unchanged | Screenshot footer — **PENDING** |

**Acceptance:** Owner attaches 4 screenshots or confirms PASS in GM thread.

---

## Blocker 5.2 — Social production readiness

Run on prod (read-only):

```bash
sudo bash /var/www/mywave/automation/production/prod_social_readiness_check.sh
```

| Check | Status |
|-------|--------|
| `SOCIAL_SPREADSHEET_ID` or fallback `SPREADSHEET_ID` | **PENDING Owner run** |
| SA access to `Social_Applications` tab | **PENDING Owner run** |
| Form writes correct Sheet (staging proved PR #33) | code OK; prod **PENDING** |
| No booking/calendar/slots from Social | **confirmed** (no imports in `social.py`) |

---

## Commands (NOT APPROVED — template)

See `docs/integration/PROD_UI_JUN2026_ROLLOUT_RUNBOOK.md`

---

## Smoke checklist (post-rollout)

1. `/health` → 200  
2. `/` desktop + mobile — hero/logo/ticker  
3. Header/footer turquoise logo  
4. `/services` — boat before gym  
5. `/social` — page loads (flags ON)  
6. Social form submit → success (staging pattern)  
7. `POST /api/blog/media/upload` → 201 (regression)  
8. journal — no Traceback 15 min  

---

## Rollback

```bash
PREV=$(cat /var/backups/mywave/head.pre_ui_rollout_<TS>.txt)
git -c safe.directory=/var/www/mywave -C /var/www/mywave checkout "$PREV"
sudo cp /var/backups/mywave/.env.pre_ui_rollout_<TS> /var/www/mywave/.env
sudo systemctl restart mywave-site
```

---

## Risk / downtime

| Item | Level |
|------|-------|
| Static asset size | Low (git pull time) |
| Social flags without Sheet | Medium — run readiness script first |
| Hero visual | Medium — blocked on Owner screenshots |
| Upload regression | Low — PR45 in base |
| **Estimated downtime** | ~30–60 s (`mywave-site` restart) |

---

## Tests (release branch)

```text
55 passed (upload, social, hero, ticker, services, blog regression)
```

---

## Guardrails

No merge PR #48, no prod rollout, no flag changes, no restart until GM/Owner final approval.
