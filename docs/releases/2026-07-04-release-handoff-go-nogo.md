# Release handoff — GO/NO-GO (PR74 deployed · PR75 hold)

**Date:** 2026-07-04  
**Owner decision:** **HOLD deploy** — один подготовленный production deploy после закрытия релизного хвоста  
**Production rule:** no server / no restart / no `.env` until Owner approves final handoff

---

## GO/NO-GO snapshot

```text
RELEASE_READY=NO
Reason: Mobile QA sign-off pending; final release checklist incomplete

Target deploy SHA (when GO): bf27da1f (main; includes PR75 `eef40bd4` + handoff doc)
Minimum SHA with PR75 fix only: eef40bd4a970f31c349794d033e048657a4e510b
Production HEAD (current, PR74): ffc08afcb20c557b0ed329db28bf49fabe265bae

Included in target bundle:
- PR74 (already on prod — admin shell)
- PR75 (MERGED, not deployed — booking mobile hotfix)

CI=PASS (PR75 merge)
Targeted tests=PASS (test_booking_confirm_slot_button.py, PR531/PR53 evidence)
Mobile QA=NO (A1/A2/I1/T1 pending)
PR56 smoke plan=ready (prod_pr56_smoke.sh)
Rollback plan=ready (see below)

Out of scope confirmed for target deploy:
- no .env
- no DB migrations
- no TGbotAdmin/node
- no runtime flags unless explicitly approved
- Notifications v2 runtime: OUT (Option A)
```

---

## Closed (no action before deploy)

| Item | Status |
|------|--------|
| PR74 Admin shell | **ACCEPTED** · deployed `ffc08afc` |
| PR74 Browser QA | **PASS** |
| PR74 Post-QA Sheets cleanup | **PASS** · backup `QA_CLEANUP_2026-07-01` |
| PR72 docs | **MERGED** `ee934d43` |
| PR75 booking hotfix | **MERGED** `eef40bd4` · **HOLD deploy** |

---

## Open before GO (blocking)

| # | Item | Owner / team action | Status |
|---|------|---------------------|--------|
| 1 | Phase 1 Mobile QA A1/A2/I1/T1 | Device run + screenshots | **PENDING** |
| 2 | PR75 booking flow verify on device | After deploy or staging mirror | **PENDING** |
| 3 | Release gate checklist | [RELEASE_GATE_CHECKLIST.md](../deployment/RELEASE_GATE_CHECKLIST.md) | **INCOMPLETE** |
| 4 | Production audit log entry | [PRODUCTION_AUDIT_LOG.md](../ops/PRODUCTION_AUDIT_LOG.md) | **PENDING** |
| 5 | Release note for combined deploy | this doc + post-deploy note | **DRAFT** |

---

## PR75 — must be in final SHA

Verify after deploy (Owner mobile):

| Check | Expected |
|-------|----------|
| HTML cache buster | `booking-mobile.css?v=booking-slot-btn1` |
| `#confirmSlotBtn` | visible (not `display: none`) |
| Boat flow | date → Далее → select set(s) → **Продолжить** → contact → **Подтвердить запись** |
| Gym flow | date → Далее → select slot → auto step 3 (no regression) |

**Root cause fixed:** `#confirmSlotBtn { display: none }` removed from `style.css`.

---

## Mobile QA — Owner checklist (this release)

**Owner acceptance criteria** (primary for GO):

| ID | Criterion | Result |
|----|-----------|--------|
| **A1** | Boat mobile booking flow — date → set → **Continue** → contact → confirm | [ ] PASS / FAIL |
| **A2** | Gym booking flow — slot → contact step (no regression) | [ ] PASS / FAIL |
| **I1** | Integration smoke / no JS modal regression (booking modals, back, close) | [ ] PASS / FAIL |
| **T1** | Telegram / Sheets / booking smoke **or explicitly not touched** in this deploy | [ ] PASS / N/A |

**Matrix mapping** (canonical platforms — [MOBILE_QA_MATRIX.md](../qa/MOBILE_QA_MATRIX.md)):

| Owner ID | Suggested device run |
|----------|----------------------|
| A1 | Android Chrome · 360×800 / 390×844 |
| A2 | Android Yandex · 360×800 |
| I1 | iPhone Safari · safe-area |
| T1 | Server smoke only (`prod_pr56_smoke.sh`) — **no Telegram/Sheets mutation** in frontend deploy |

**PR75 verify on device:** `booking-mobile.css?v=booking-slot-btn1` · `#confirmSlotBtn` visible on boat step 2.

**Environment:** incognito · VPN off · hard refresh.

**Screenshots:** `docs/qa/screenshots/2026-07-04/`

---

## Notifications v2 — decision

**Selected: Option A (default, safe)**

```text
Notifications v2 runtime НЕ входит в ближайший deploy.
Остаётся отдельным PR после Owner review.
SOCIAL_ADMIN_NOTIFICATIONS_ENABLED stays OFF on prod.
```

Prep only: [NOTIFICATIONS_V2_PREP.md](../integration/NOTIFICATIONS_V2_PREP.md) (PR72).

Option B (only if Owner explicitly approves later): feature flag, dry-run tests, Telegram spam protection, rollback plan — **not in this bundle**.

---

## Admin stubs — decision

**Selected: ACCEPTED as current scope**

```text
Blog / Events / Users / Settings = stub pages ("Раздел готовится").
Not blocking PR75 deploy or release GO.
Future full sections = separate roadmap PRs (not this release).
```

Evidence: [pr74/README.md](../evidence/pr74/README.md)

---

## Release type (target deploy)

| Field | Value |
|-------|-------|
| Type | **frontend** (CSS + template cache busters) |
| Runtime | unchanged (frozen baseline) |
| Mixed deploy | **NO** |

---

## Rollback plan

| | |
|---|---|
| **PREV (prod today)** | `ffc08afc` (PR74 admin shell) |
| **TARGET** | `eef40bd4` (PR75 booking hotfix) |
| **Rollback command** | `git checkout ffc08afc && systemctl restart mywave-site` |
| **Verify rollback** | `prod_pr56_smoke.sh` · boat flow regresses to hidden Continue (known) |

---

## Smoke plan (on deploy day only — not now)

```bash
# On server after Owner GO (do not run during HOLD)
cd /var/www/mywave
git fetch origin && git checkout eef40bd4a970f31c349794d033e048657a4e510b
sudo systemctl restart mywave-site
bash automation/production/prod_pr56_smoke.sh
curl -sS http://127.0.0.1:5000/ | grep -o 'booking-mobile.css[^"]*'
# expect: booking-mobile.css?v=booking-slot-btn1
```

Public: https://mywavewake.ru/health/live · https://mywavewake.ru/

---

## Links

| Resource | URL |
|----------|-----|
| PR75 | https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/75 |
| PR74 evidence | [docs/evidence/pr74/README.md](../evidence/pr74/README.md) |
| Release gate | [docs/deployment/RELEASE_GATE_CHECKLIST.md](../deployment/RELEASE_GATE_CHECKLIST.md) |
| Mobile QA matrix | [docs/qa/MOBILE_QA_MATRIX.md](../qa/MOBILE_QA_MATRIX.md) |
| Platform state | [docs/PLATFORM_STATE.md](../PLATFORM_STATE.md) |

---

## When to flip RELEASE_READY=YES

Owner confirms:

1. A1/A2/I1/T1 **PASS** (booking flows + matrix sections)  
2. Release gate checklist **complete**  
3. Rollback SHA **recorded**  
4. Explicit **GO** for single deploy to `bf27da1f` (or newer `main` ≥ `eef40bd4`)

Then team sends final one-line:

```text
RELEASE_READY=YES
Target deploy SHA=<sha>
Owner GO received: YES
```
