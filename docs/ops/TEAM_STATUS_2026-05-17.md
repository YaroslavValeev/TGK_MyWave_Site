# Team status — production & Phase 1 (GM brief)

**Production:** https://mywavewake.ru  
**Date:** 2026-05-17 (sync с GM execution plan)  
**Runtime baseline:** `3de56f8c` **FROZEN**  
**Living QA board:** [PHASE1_MOBILE_QA_STATUS.md](../qa/PHASE1_MOBILE_QA_STATUS.md)  
**Latest on `origin/main`:** `c8101ae2` — final checklist art `1976d637` (~53/62 cards) · code `cardbg14` (`ad9f2b80`)  
**Production server:** deploy target only — `git pull`, **no** `commit`/`push` с сервера

---

## 1. Текущее состояние

### Runtime

| Item | Value |
|------|--------|
| Baseline | `3de56f8c` |
| Status | **FROZEN** |
| Governance | соблюдается, нарушений freeze-policy не выявлено |

---

## 2. Production status (подтверждено)

| Проверка | Статус |
|----------|--------|
| frontend deploy | OK |
| `mobile-home.css?v=3` | OK |
| checklist assets / `cardbg14` | OK |
| отзывы / реальные фото | OK |
| `production_smoke.sh` | PASS |
| `verify_production_frontend.sh` | PASS |
| health / blog / static | OK |
| governance discipline | ACTIVE |

---

## 3. Checklist cards

Pipeline:

```text
card → mapping → js → img render → production
```

- Assets: HTTP 200, маппинг через `checklist.js`, колонка иллюстрации на проде **работает** (см. QA screenshot).
- Текущие webp — **placeholder-level art** (градиент + подпись категории).
- Статус слоёв: `deploy OK` · `render OK` · **`content NOT OK`** — не технический блокер.
- Это **не** deploy / cache / runtime issue; **не** менять `checklist.js` / mapping / backend.
- Следующий шаг: **in-place замена** webp — [CHECKLIST_FINAL_ART_REPLACEMENT.md](CHECKLIST_FINAL_ART_REPLACEMENT.md) + [CHECKLIST_ART_FILE_MANIFEST.txt](CHECKLIST_ART_FILE_MANIFEST.txt) (55 файлов).

---

## 4. Blog / smoke

| Item | Классификация |
|------|----------------|
| Ошибка tooling `Unable to parse range: raw_feed!A1:ZZ1000` | **P2** (диагностический скрипт) |
| Production stability | не затронута |
| Runtime | не меняем |

Исправление P2: `scripts/blog_raw_feed_smoke_check.py` — quoted range + fallback A1:Z1000 / A1:T2000.

Контент блога: витрина пуста, если в live Sheets нет publishable строк; по xlsx `(3)` — **24** из **63** готовы ([blog_xlsx_publishable_list.json](../../reports/blog_xlsx_publishable_list.json)). Phase 2 — blog visibility polish + синхронизация Sheets.

---

## 5. Phase 1 — единственный blocker

```text
REAL DEVICE QA
```

**Ready for release gate:** NO (`governance-incomplete`)

---

## 6. Обязательный manual QA

| Platform |
|----------|
| Android Chrome |
| Android Yandex |
| iPhone Safari |
| Tablet |

**Зоны:** hero · carousel swipe · overlays · clipping · checklist cards · contacts · reviews · chat floating · safe-area · tablet layout.

**Артефакты после PASS:**

- [MOBILE_QA_RUN_2026-05-15.md](../qa/MOBILE_QA_RUN_2026-05-15.md)
- [MOBILE_QA_MATRIX.md](../qa/MOBILE_QA_MATRIX.md)
- `docs/qa/screenshots/2026-05-15/`

---

## 7. Post-deploy policy (mandatory)

Deploy **не завершён** без:

1. `production_smoke.sh` PASS  
2. Mobile QA PASS (4 платформы)  
3. release note  
4. [PRODUCTION_AUDIT_LOG.md](PRODUCTION_AUDIT_LOG.md)

---

## 8. Запрещено до stabilization exit

Runtime refactor · backend rewrite · websocket · Redis · booking API · mixed runtime/frontend deploy · architecture experiments · aggressive optimization.

**Backend/runtime change** только при: issue + rollback + smoke strategy + production justification + explicit approval → иначе **CHANGE REJECTED**.

---

## 9. Roadmap

| Phase | Focus |
|-------|--------|
| **1** (текущая) | Mobile QA sign-off — **blocker: devices** |
| **2** | Checklist final webp · reviews polish · blog visibility |
| **3** | fail2ban · UFW · backup · observability · alerts · CI/CD |
| **4** | ownership · release governance · incident · audit consistency |

**Главный актив:** predictable deploys · rollback confidence · governance · release traceability · QA consistency.

---

## 10. Phase status (canon)

| Phase | Status |
|-------|--------|
| Runtime stabilization | DONE |
| Frontend pipeline | DONE |
| Checklist render pipeline | DONE |
| Production deploy flow | DONE |
| Manual device QA | **PENDING** |
| Final design assets (webp) | **PARTIAL** — в `main`, на prod после `git pull`; 9 participant ещё placeholder |

## 11. Deploy flow (mandatory)

```text
ПК / Cursor → git push → GitHub origin/main → git pull → production server
```

Push rejected `(fetch first)` на сервере = remote новее локальной копии, **не** auth-incident. Дополнительный push с prod **не нужен** после `git pull`.

## 12. Следующее действие

1. **Дизайн:** финальные webp → `static/images/Project/Cards/checklist/` (манифест).  
2. **ПК:** `git add` → `commit` → `push`.  
3. **Сервер:** только `git pull` + `restart` — [SERVER_CHECKLIST_ART_DEPLOY.md](SERVER_CHECKLIST_ART_DEPLOY.md).  
4. **QA:** REAL DEVICE QA (4 платформы) → matrix → sign-off Phase 1.

**Runbooks:** [SERVER_RUNBOOK_BLOG_CHECKLIST_2026-05-17.md](SERVER_RUNBOOK_BLOG_CHECKLIST_2026-05-17.md) · [SERVER_DEPLOY_2026-05-16.md](SERVER_DEPLOY_2026-05-16.md)
