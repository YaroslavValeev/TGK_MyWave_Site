# MyWave Online Coaching — PR / Merge Report

**Branch (local):** `main` — рекомендуется feature-branch перед push, напр. `feat/online-coaching-mvp`  
**Date:** 2026-07-05  
**Status:** GREEN — ready for commit / push / Owner deploy

---

## Pre-merge checks

| Check | Result |
|-------|--------|
| Online Coaching tests (30) | ✅ passed |
| Booking/Social regression (27) | ✅ passed |
| Fast route smoke (`scripts/smoke_online_coaching_routes.py`) | ✅ 10 routes |
| `.gitignore` conflict markers | ✅ none |
| Secrets in diff (`.env`, tokens, SA JSON) | ✅ none |
| TGbotAdmin / `app/routes/telegram/` | ✅ unchanged |
| Node-chat / `app/routes/chat.py` | ✅ unchanged |
| T-Bank | ✅ Phase 1 semi-manual only |
| WhatsApp/MAX | ✅ store-only, no automation |

---

## Changed files (Online Coaching scope)

### Modified (7)
- `app/__init__.py` — register blueprints
- `app/services/notifications.py` — `send_telegram_notification_with_keyboard`
- `configs/services.yaml` — card `online_coaching`
- `env.example` — feature flags + sheet names
- `templates/admin/base.html` — admin nav link
- `templates/index.html` — `page_url` for services
- `templates/services.html` — `page_url` for services

### Added (22)
- `app/config/online_coaching_features.py`
- `app/routes/online_coaching.py`
- `app/routes/admin/online_coaching.py`
- `app/services/online_coaching_{schema,store,notifications,payments,admin}.py`
- `templates/services/online_coaching.html`
- `templates/admin/online_coaching/{list,detail}.html`
- `static/css/online-coaching.css`
- `static/js/online-coaching-form.js`
- `scripts/ensure_online_coaching_sheets.py`
- `scripts/smoke_online_coaching_routes.py`
- `docs/deploy/ONLINE_COACHING_DEPLOY.md`
- `docs/products/ONLINE_COACHING_{SPEC,PREBUILD_REPORT}.md`
- `tests/unit/test_online_coaching_*.py` (5 files)

### Exclude from this PR
- `docs/releases/2026-07-04-release-handoff-go-nogo.md` — unrelated (line endings only); do not stage

---

## Tests run

```bash
pytest tests/unit/test_online_coaching_*.py -q                    # 30 passed
pytest tests/unit/test_social_features.py \
     tests/unit/test_booking_phase1.py \
     tests/unit/test_pr56_boot_regression.py -q                 # +27 passed

DISABLE_TELEGRAM=1 ENABLE_GOOGLE_SERVICES=0 ONLINE_COACHING_ENABLED=1 \
  python scripts/smoke_online_coaching_routes.py               # count=10
```

---

## Risks

| Risk | Mitigation |
|------|------------|
| Sheets tabs missing | `ensure_online_coaching_sheets.py` dry-run + APPLY |
| PII in Telegram | `sanitize_record_for_telegram()` |
| Accidental prod enable | flags OFF by default |
| T-Bank API absent | semi-manual admin flow |
| Flask smoke timeout | dedicated fast smoke script |

---

## Production commands (Owner)

```bash
cd /var/www/mywave
git fetch origin && git pull origin <branch-with-online-coaching>
# set ONLINE_COACHING_*=1 in .env
source venv/bin/activate
python scripts/ensure_online_coaching_sheets.py
ONLINE_COACHING_SHEETS_APPLY=1 python scripts/ensure_online_coaching_sheets.py
DISABLE_TELEGRAM=1 ENABLE_GOOGLE_SERVICES=0 ONLINE_COACHING_ENABLED=1 \
  python scripts/smoke_online_coaching_routes.py
pytest tests/unit/test_online_coaching_*.py -q
sudo systemctl restart mywave-site
curl -sI https://mywavewake.ru/services/online-coaching | head -5
```

**Rollback:** `ONLINE_COACHING_ENABLED=0` + restart.

---

## Suggested commit message

```
feat(online-coaching): MVP landing, apply API, admin UI, Sheets + Telegram

Add MyWave Online Coaching direction with semi-manual T-Bank payments,
feature flags default OFF, and 30 unit tests.
```
