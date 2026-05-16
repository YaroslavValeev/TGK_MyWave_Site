# Team status — production & Phase 1 (GM brief)

**Production:** https://mywavewake.ru  
**Date:** 2026-05-17  
**Runtime baseline:** `3de56f8c` **FROZEN**  
**Living QA board:** [PHASE1_MOBILE_QA_STATUS.md](../qa/PHASE1_MOBILE_QA_STATUS.md)

---

## 1. Текущий статус

### Runtime

- Baseline: `3de56f8c`
- Status: **FROZEN**
- Runtime governance соблюдается; нарушений freeze-policy не выявлено.

### Frontend deploy

Подтверждено на production:

- `mobile-home.css?v=3`
- checklist assets доступны (HTTP 200, mapping OK)
- `qa_mobile_precheck.sh` — **PASS**
- `production_smoke.sh` — **PASS**
- static assets отдаются корректно
- server sync стабилен (`git pull` + `restart`)

Дополнительно (17.05): фото учеников в отзывах восстановлены (`images/students`, `3d718a00`); checklist render via `<img>` (`cardbg13`, `ad71c02b`).

---

## 2. Checklist cards

**Подтверждено:** `/static/images/Project/Cards/checklist/` — файлы есть, 200, привязка `checklist.js` → `card -> mapping -> js -> asset -> img -> prod`.

**Важно:** текущие webp — **placeholder-level**. Это не deploy/runtime/cache bug; ожидаемо до финального art-pack от дизайна. Pipeline **READY** — финальные webp можно заменить без изменения runtime.

---

## 3. Mobile v3

На проде: mobile baseline, carousel, hero, contacts, chat safe-area, reviews layout. HTML: `mobile-home.css?v=3`.

---

## 4. Phase 1

| Automated | Status |
|-----------|--------|
| qa_mobile_precheck | PASS |
| production_smoke | PASS |
| static / checklist checks | PASS |

**BLOCKER:** только **REAL DEVICE QA** (A1/A2/I1/T1).  
**Ready for release gate:** **NO** до PASS на всех платформах.

---

## 5. Manual QA — обязательно

Платформы: Android Chrome · Android Yandex · iPhone Safari · Tablet.

Зоны: hero · carousel swipe · overlays · clipping · checklist cards · contacts · reviews · chat · safe-area · tablet.

Артефакты:

- [MOBILE_QA_RUN_2026-05-15.md](../qa/MOBILE_QA_RUN_2026-05-15.md)
- [MOBILE_QA_MATRIX.md](../qa/MOBILE_QA_MATRIX.md)
- Screenshots: `docs/qa/screenshots/2026-05-15/`

---

## 6. Post-deploy governance

Deploy **не завершён** без:

1. `production_smoke` PASS  
2. Mobile QA PASS (4 платформы)  
3. release note  
4. [PRODUCTION_AUDIT_LOG.md](PRODUCTION_AUDIT_LOG.md)  

---

## 7. Запрещено до stabilization exit

Runtime refactor · backend rewrite · websocket/booking/Redis changes · mixed runtime/frontend deploy · «быстрые оптимизации» без governance.

---

## 8. Следующие фазы

| Phase | Focus |
|-------|--------|
| 2 | Checklist final art · reviews polish · blog visibility |
| 3 | P2 hardening (fail2ban, UFW, backup, observability, CI/CD) |
| 4 | Operational maturity (ownership, release, incident, audit) |

---

## 9. Главный акцент

Актив платформы: **predictable deploys · rollback confidence · governance · release traceability · operational maturity** — сохранять при всех изменениях.

---

## 10. Следующее действие команды

```text
Закрыть REAL DEVICE QA.
```

После PASS: обновить matrix → sign-off → Phase 1 formally completed.

**Server runbook:** [SERVER_DEPLOY_2026-05-16.md](SERVER_DEPLOY_2026-05-16.md)
