# PR #48 — Final evidence package (GM review)

**Status:** REVIEW ONLY — **Execution NOT STARTED**  
**PR:** https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/48  
**Release branch:** `release/prod-ui-jun2026`  
**Date:** 2026-06-18 (updated after HEAD sync + Sheets canon)

---

## §6 Final package block

```text
Current prod HEAD:        ae4b6272 (PR45 hotfix; server unchanged since rollout)
Target release HEAD:      797c7f5d (release/prod-ui-jun2026 tip)
origin/main HEAD:         0274a54e (PR45 + deploy.yml safety only)

Diff stat (ae4b6272..797c7f5d):  98 files, +124035 / −95
Diff name-only count:     98
Events leakage check:     PASS
DB migration check:       PASS
Sheets canon committed:   yes (SHEETS_ID_CANON.md, env.example, config.py, readiness script, oneshot)
Evidence docs updated:  yes (this file + runbook target HEAD synced)
Hero screenshots:         PENDING Owner
Social readiness result:  PENDING Owner (Option A one-shot)
Execution status:         NOT STARTED
```

**Verify target on branch tip:**

```bash
git fetch origin release/prod-ui-jun2026
git rev-parse origin/release/prod-ui-jun2026
git diff --stat ae4b6272..origin/release/prod-ui-jun2026
git diff --name-only ae4b6272..origin/release/prod-ui-jun2026 | wc -l
```

---

## Commit lineage (release branch, after Sheets canon)

| Commit | Subject |
|--------|---------|
| `708bf67f` | docs: fix PR48 rollout runbook target HEAD |
| `49bfbcc8` | docs: PR48 final evidence package and social readiness script |
| `bd9f303b` | docs: prod UI jun2026 rollout runbook (not executed) |
| UI cherry-picks | `2ce34417` … `7a368986` (Social, hero, ticker, brand, services) |
| **+ canon commit** | `1eec2a4d` — Sheets ID canon, oneshot readiness, evidence sync |
| **+ HEAD pin** | `797c7f5d` — evidence/runbook target HEAD (tip) |

**Evidence docs commit:** `797c7f5d`  
**Runbook commit:** `708bf67f` + `797c7f5d`

---

## Diff name-only manifest (98 files at branch tip)

**App / config:**  
`app/__init__.py`, `app/config/social_features.py`, `app/routes/api.py`, `app/routes/brand.py`, `app/routes/services.py`, `app/routes/social.py`, `app/services/blog/publish.py`, `app/services/blog/store.py`, `app/services/brand/*`, `app/services/competitions/store.py`, `app/services/competitions/visibility.py`, `app/services/social_*.py`, `config.py`, `configs/services.yaml`, `env.example`

**Docs:**  
`docs/integration/BLOG_MEDIA_BACKFILL_RUNBOOK.md` (docs-only, no backfill execution), `PROD_UI_JUN2026_ROLLOUT_RUNBOOK.md`, `PR48_FINAL_EVIDENCE_PACKAGE.md`, `SHEETS_ID_CANON.md`, `PROD_SOCIAL_READINESS_ONESHOT.md`, `SOCIAL_MISSION_STAGING_UI_EVIDENCE.md`, `SOCIAL_PR1_DATA_LAYER.md`

**Automation:**  
`automation/production/prod_social_readiness_check.sh`

**Static (code):**  
`static/css/branding.css`, `competitions-ticker.css`, `mobile-home.css`, `social-mission.css`, `static/js/competitions-ticker.js`, `social-application-form.js`

**Templates:**  
`templates/base.html`, `index.html`, `partials/brand_logo.html`, `home_competitions_ticker.html`, `legal_consent.html`, `social_*`, `social/index.html`

**Tests:**  
`tests/conftest.py`, `test_blog_media_regression.py`, `test_brand_logo_package.py`, `test_competitions_ticker.py`, `test_home_hero_logo.py`, `test_services_order.py`, `test_social_*.py`

**Logo package (binary-heavy):**  
`static/images/logotip_MyWave/MyWave_logo_package_brand_turquoise/**` (43 binary paths: png, svg, pdf, eps, tif, jpg, webm, mov, mp4)

---

## Large static / binary manifest

| Category | Count | Notes |
|----------|-------|--------|
| PNG/JPG/WebP | ~30 | Logo masters + previews |
| SVG | 6 | In-repo text |
| PDF/EPS/TIF | 8 | Print outdoor |
| Video (webm/mov/mp4) | 4 | Brand reveal (~8 MB mov) |
| EPS vector dumps | 2 | Large line-count in git stat |

**Runtime-critical:** turquoise SVG + PNG in `brand_logo.html`; video not required for homepage.

---

## Events leakage check

```bash
git diff ae4b6272..origin/release/prod-ui-jun2026 --name-only \
  | grep -Ei 'events|classifier|events_features' || echo PASS
# Result: (empty) PASS
```

**Included (ticker only):** `competitions/store.py`, `competitions/visibility.py`, `home_competitions_ticker.html`, `competitions-ticker.js/css`

**Excluded:** `events_features.py`, `app/routes/events*`, `templates/events*.html`

---

## DB migration check

```bash
git diff ae4b6272..origin/release/prod-ui-jun2026 --name-only -- migrations/
# Result: (empty) PASS — no flask db upgrade for this rollout
```

---

## Blog media / backfill

Owner decision — **no execution in PR #48:**

```text
13 old review_media rows: Place1Logo / fallback — keep
Manual covers / Sheet writeback / backfill: no
```

---

## Flags (after execution approval + Social readiness PASS)

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

Apply after merge + restart; backup `.env` first.

---

## Blocker 5.1 — Hero logo visual sign-off

| Check | Owner evidence |
|-------|----------------|
| Desktop hero logo fully visible | **PENDING** |
| Mobile hero logo not clipped | **PENDING** |
| Header logo unchanged (turquoise brand) | **PENDING** |
| Footer logo unchanged | **PENDING** |

**Acceptance:** 4 screenshots or Owner text PASS in GM thread.

---

## Blocker 5.2 — Social production readiness

**Canon:** `docs/integration/SHEETS_ID_CANON.md`

| Check | Expected | Status |
|-------|----------|--------|
| `SPREADSHEET_ID` tail | `akVMOrCgic0`, one line | **PENDING Owner** |
| `PARSER_NEWS_SPREADSHEET_ID` tail | `LijNNyn50` | **PENDING Owner** |
| Social effective tail | `akVMOrCgic0` | **PENDING Owner** |
| No duplicate `SPREADSHEET_ID` | count = 1 | **PENDING Owner** |
| SA → `Social_Applications` tab | YES | **PENDING Owner** |
| Social → Admin not Parser | code + env | **PENDING Owner** |
| No booking/calendar from Social | no imports in `social.py` | **confirmed** |

**Owner command (Option A — preferred, read-only):**  
`docs/integration/PROD_SOCIAL_READINESS_ONESHOT.md`

After PR #48 on prod: `sudo bash automation/production/prod_social_readiness_check.sh`

---

## Commands (NOT APPROVED — template)

`docs/integration/PROD_UI_JUN2026_ROLLOUT_RUNBOOK.md`

---

## Smoke checklist (post-rollout)

1. `/health` → 200  
2. `/` desktop + mobile — hero/logo/ticker  
3. Header/footer turquoise logo  
4. `/services` — boat before gym  
5. `/social` — page loads (flags ON)  
6. Social form submit → success  
7. `POST /api/blog/media/upload` → 201  
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

## Tests (release branch)

```text
55 passed (upload, social, hero, ticker, services, blog regression)
```

---

## Guardrails

No merge PR #48, no prod rollout, no flag changes, no restart until GM/Owner final approval.
