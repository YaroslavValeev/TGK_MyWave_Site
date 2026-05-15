# Phase 1 — Mobile QA Status (living)

**Production:** https://mywavewake.ru  
**Phase status:** `IN PROGRESS — BLOCKER`  
**Roadmap:** [ENGINEERING_MATURITY_ROADMAP.md](../deployment/ENGINEERING_MATURITY_ROADMAP.md)  
**Runtime:** `3de56f8c` FROZEN — не трогать

| Governance | Commit |
|------------|--------|
| Canon | `af153b05` |
| Acknowledgment | `a96e0ff9` |
| Automated precheck | `000a7100` |
| Audit refs | `8cb70d96` |

---

## Сводка

| Layer | Status |
|-------|--------|
| Runtime | operational |
| Governance | operational |
| Frontend QA phase | **NOT complete** |
| Sign-off | **NO** — Ready for release gate |

---

## Step 0 — Frontend deploy — **CLOSED**

- [x] `git pull` → templates `?v=3` on disk  
- [x] `sudo systemctl restart mywave-site` (не `reload` — unit без ExecReload)  
- [x] Production HTML: `mobile-home.css?v=3` (verified)  
- [x] `production_smoke.sh` → PASS  

После `git pull` (fix precheck gzip): `bash scripts/qa_mobile_precheck.sh`  
Если `curl | grep mobile-home` показывает `?v=3`, а скрипт FAIL — обновите скрипт: `git pull`

Детали: [MOBILE_QA_AUTOMATED_PRECHECK_2026-05-15.md](MOBILE_QA_AUTOMATED_PRECHECK_2026-05-15.md)

---

## Automated pre-check (выполнено)

| Проверка | Result |
|----------|--------|
| production_smoke.sh | PASS |
| `/` | 200 |
| `/blog` | 200 |
| `/projects/checklist-org` | 200 |
| mobile-home.css (static, ?v=3) | 200 |
| checklist.css | 200 |
| Home HTML `?v=3` | **PASS** (after restart) |

---

## Step 1 — Manual device QA (после `?v=3` на prod)

| Platform | Status |
|----------|--------|
| Android Chrome (A1) | PENDING |
| Android Yandex (A2) | PENDING |
| iPhone Safari (I1) | PENDING |
| Tablet (T1) | PENDING |

**Обязательно:** инкогнито · hard refresh · verify `mobile-home.css?v=3`

**Зоны:** hero · carousel/cards · contacts · chat · checklist · reviews · safe-area · overlays · clipping · tablet

**Screenshots:** `docs/qa/screenshots/2026-05-15/`

**Артефакты:** [MOBILE_QA_RUN_2026-05-15.md](MOBILE_QA_RUN_2026-05-15.md) · [MOBILE_QA_MATRIX.md](MOBILE_QA_MATRIX.md)

Заменить `PENDING` → `PASS` / `FAIL` → **Ready for release gate: YES**

---

## Post-deploy policy (frontend release)

Deploy governance-incomplete без:

1. [PRODUCTION_AUDIT_LOG.md](../ops/PRODUCTION_AUDIT_LOG.md)  
2. Release note в [releases/](../releases/)  
3. `production_smoke.sh` PASS  
4. Mobile QA PASS (все 4 платформы)  

---

## После Phase 1

| Phase | Focus |
|-------|--------|
| 2 | Checklist visuals · reviews · blog visibility (`frontend` / `content`) |
| 3 | Hardening · observability · CI/CD (`ops`) |
| 4 | Ownership · release · incident maturity |

До stabilization exit: никаких runtime refactor · mixed deploys · backend rewrites.
