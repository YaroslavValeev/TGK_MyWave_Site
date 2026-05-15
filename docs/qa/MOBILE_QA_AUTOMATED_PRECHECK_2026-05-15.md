# Mobile QA — Automated Pre-check (2026-05-15)

**Production:** https://mywavewake.ru  
**Run by:** Cursor agent (remote)  
**Script:** `scripts/qa_mobile_precheck.sh`  
**Does NOT replace:** real device QA (A1/A2/I1/T1)

---

## Results

| Check | Result | Notes |
|-------|--------|-------|
| `production_smoke.sh` | **PASS** | home, blog, health, slots, static review — 200 |
| Home `/` | **PASS** | HTTP 200 |
| Blog `/blog` | **PASS** | HTTP 200 |
| Checklist `/projects/checklist-org` | **PASS** | HTTP 200 |
| `mobile-home.css` (static file) | **PASS** | HTTP 200 with `?v=3` |
| `checklist.css` | **PASS** | HTTP 200 |
| Home HTML links `mobile-home.css` | **FAIL** | Production HTML: `?v=2` — repo canon: `?v=3` |

---

## Blocker для Phase 1 QA

На production **ещё не задеплоен** frontend baseline с `templates/base.html` → `mobile-home.css?v=3`.

**Рекомендуемое действие (frontend release, не runtime refactor):**

```bash
cd /var/www/mywave
git fetch origin && git pull --ff-only origin main
# убедиться: grep mobile-home templates/base.html  →  ?v=3
sudo systemctl reload mywave-site   # templates pick-up
curl -sS https://mywavewake.ru/ | grep mobile-home
```

После подтверждения `?v=3` в HTML — выполнить manual device QA.

---

## Device QA status

| Platform | UX sections | Status |
|----------|-------------|--------|
| A1 Android Chrome | all | **PENDING** (manual) |
| A2 Android Yandex | all | **PENDING** (manual) |
| I1 iPhone Safari | all | **PENDING** (manual) |
| T1 Tablet | all | **PENDING** (manual) |

**Sign-off:** Ready for release gate: **NO**
