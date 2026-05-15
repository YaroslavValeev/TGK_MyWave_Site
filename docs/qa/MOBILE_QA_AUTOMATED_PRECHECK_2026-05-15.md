# Mobile QA — Automated Pre-check (2026-05-15)

**Production:** https://mywavewake.ru  
**Run by:** Cursor agent (remote)  
**Script:** `scripts/qa_mobile_precheck.sh`  
**Does NOT replace:** real device QA (A1/A2/I1/T1)  
**Precheck fixes:** `3ae20741` (`--compressed`) · `f3a5256b` (`grep -Fq`) · `dc08c500` (HTML first)  
**Status:** Step 0 closed on prod (manual curl `?v=3`) · script **PASS** after `git pull` → `dc08c500`  
**Server runbook:** [SERVER_PHASE1_VERIFY.md](SERVER_PHASE1_VERIFY.md)

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
| Home HTML links `mobile-home.css` | **PASS** (after restart) | `?v=3` confirmed on prod |
| Home HTML `?v=3` | **PASS** | Step 0 closed 2026-05-15 |

---

## Step 0 — CLOSED

После `git pull` + `sudo systemctl restart mywave-site` production отдаёт:

```html
<link rel="stylesheet" href="/static/css/mobile-home.css?v=3" />
```

**Примечание:** `systemctl reload` не работает для `mywave-site` (нет ExecReload) — нужен **restart**.

Перепроверка: `bash scripts/qa_mobile_precheck.sh` → ожидается `PRECHECK OK`.

---

## Следующий шаг: manual device QA

---

## Device QA status

| Platform | UX sections | Status |
|----------|-------------|--------|
| A1 Android Chrome | all | **PENDING** (manual) |
| A2 Android Yandex | all | **PENDING** (manual) |
| I1 iPhone Safari | all | **PENDING** (manual) |
| T1 Tablet | all | **PENDING** (manual) |

**Sign-off:** Ready for release gate: **NO**
