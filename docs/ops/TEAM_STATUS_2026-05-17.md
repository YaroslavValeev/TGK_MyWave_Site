# Team status — production & Phase 1 (GM brief)

**Production:** https://mywavewake.ru  
**Date:** 2026-05-17 (sync с GM execution plan)  
**Runtime baseline:** `3de56f8c` **FROZEN**  
**Living QA board:** [PHASE1_MOBILE_QA_STATUS.md](../qa/PHASE1_MOBILE_QA_STATUS.md)  
**Latest frontend deploy:** `ad9f2b80` (checklist `cardbg14`, blog xlsx reports)

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
- Это **не** deploy / cache / runtime issue.
- Финальный visual polish — **финальные webp от дизайна** в `static/images/Project/Cards/checklist/`.

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

## 10. Следующее действие

```text
Закрыть REAL DEVICE QA на 4 платформах.
```

После PASS → matrix + sign-off → Phase 1 formally closed → Phase 2 execution.

**Runbooks:** [SERVER_RUNBOOK_BLOG_CHECKLIST_2026-05-17.md](SERVER_RUNBOOK_BLOG_CHECKLIST_2026-05-17.md) · [SERVER_DEPLOY_2026-05-16.md](SERVER_DEPLOY_2026-05-16.md)
