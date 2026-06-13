# Events-3 — Owner/VPS Staging Runbook (copy-paste)

**Audience:** Owner / ops on VPS  
**Site-only.** TGbotAdmin runtime **not** involved.  
**Production:** do **not** touch `/var/www/mywave`, `mywave-site`, bot, node.

**Expected develop HEAD after PR #26:** `eb2ab0ca` or newer (includes `scripts/staging_events_qa.sh`).

---

## 0. Safety — never run on production

```bash
# ❌ DO NOT RUN on prod path / prod services:
# cd /var/www/mywave
# sudo systemctl restart mywave-site
# sudo systemctl restart mywave-node.service
# sudo systemctl restart mywave-telegram-bot.service
# flask db upgrade   # in /var/www/mywave
```

**Only path:** `/var/www/mywave-staging` + `mywave-staging.service`

---

## 1. Deploy develop to staging

```bash
export STAGING_ROOT=/var/www/mywave-staging
cd "$STAGING_ROOT"

sudo -u www-data git fetch origin develop
sudo -u www-data git checkout develop
sudo -u www-data git pull --ff-only origin develop

git rev-parse HEAD
# Record output for evidence (expect eb2ab0ca+)
```

---

## 2. Staging flags (edit staging .env only)

```bash
sudo nano "$STAGING_ROOT/.env"
```

Add or update (no secrets in reports):

```text
EVENTS_API_ENABLED=1
EVENTS_PUBLIC_UI_ENABLED=1
EVENTS_REVIEW_API_ENABLED=0
EVENTS_CLASSIFIER_ENABLED=0
PUBLIC_SITE_BASE_URL=https://mywavewake.ru
ENABLE_GOOGLE_SERVICES=1
```

Verify (no values logged if sensitive):

```bash
grep -E '^EVENTS_|^PUBLIC_SITE_BASE_URL=|^ENABLE_GOOGLE_SERVICES=' "$STAGING_ROOT/.env"
```

Restart **staging only:**

```bash
sudo systemctl restart mywave-staging
sudo systemctl is-active mywave-staging
curl -fsS -o /dev/null -w "health %{http_code}\n" http://127.0.0.1:5002/ || true
```

---

## 3. Automated curl QA

```bash
cd "$STAGING_ROOT"
export STAGING_BASE_URL="https://staging.mywavewake.ru"
# If no public DNS: ssh -L 5002:127.0.0.1:5002 user@host
# export STAGING_BASE_URL="http://127.0.0.1:5002"

bash scripts/staging_events_qa.sh | tee /tmp/events3-staging-qa.log
```

Save log path in evidence. Do **not** paste secrets from `.env` or logs.

---

## 4. Manual checks (required)

| Step | Command / URL | Pass |
|------|----------------|------|
| Dynamic list | Open `/events` | Cards from Sheets; filters visible |
| Detail | Click card → `/events/<slug>` | 200, title, dates |
| 301 slug | Old title slug + same id tail | Redirect to canonical |
| Redirect | `curl -I …/competitions` | **302** → `type=competition` |
| needs_review | Row in review-queue only (API) | **Not** on public `/events` |
| Ticker | Home page | No broken `/events/...` links |
| YAML fallback | Set flags OFF, restart staging | `/events` YAML mode |
| Mobile | Browser 375px | Screenshots → `docs/integration/evidence/events-3-staging/` |
| SEO | View source | `canonical` → `https://mywavewake.ru/events…` |
| Sitemap | `curl …/sitemap.xml \| grep events` | `/events` + slugs when flags ON |
| Logs | `journalctl -u mywave-staging -n 100 --no-pager` | No Traceback; no raw payload dumps |

---

## 5. Screenshot checklist

Save to repo path (after SCP) or attach to GM report:

```text
docs/integration/evidence/events-3-staging/events-list-mobile.png
docs/integration/evidence/events-3-staging/events-detail-mobile.png
docs/integration/evidence/events-3-staging/home-ticker-mobile.png
docs/integration/evidence/events-3-staging/events-filters-mobile.png
```

---

## 6. Rollback (staging)

```bash
cd "$STAGING_ROOT"
sudo sed -i 's/^EVENTS_PUBLIC_UI_ENABLED=.*/EVENTS_PUBLIC_UI_ENABLED=0/' .env
sudo sed -i 's/^EVENTS_API_ENABLED=.*/EVENTS_API_ENABLED=0/' .env
sudo systemctl restart mywave-staging
curl -fsS -o /dev/null -w "events %{http_code}\n" http://127.0.0.1:5002/events
# Expect 200 YAML mode; /events/test-slug → 404; /competitions → 404
```

Document: `Rollback tested: yes` in evidence.

---

## 7. Fill evidence for Site/GM

Update: `docs/integration/EVENTS_PR3_STAGING_QA_EVIDENCE.md`  
Template section §1 — set PASS/FAIL per row, attach screenshots, paste sanitized log summary.

Send Site team:

```text
QA status: PASS | PARTIAL | FAIL
HEAD: <git rev-parse HEAD>
Flags: as §2
Script log: /tmp/events3-staging-qa.log summary
Blockers: (if any)
Production touched: no
```

---

## 8. Optional: staging db upgrade

Only if staging app errors on missing tables — **inside staging root only:**

```bash
cd "$STAGING_ROOT"
source venv/bin/activate
FLASK_APP=app:create_app FLASK_ENV=production flask db upgrade
```

Report separately in evidence. **Never** run in `/var/www/mywave`.

---

## Related

- `EVENTS_PR3_STAGING_QA_PACKAGE.md` — full checklist  
- `EVENTS_PR3_STAGING_QA_EVIDENCE.md` — evidence template  
- `BOOKING_PHASE2_STAGING_BOOTSTRAP_RUNBOOK.md` — staging bootstrap
