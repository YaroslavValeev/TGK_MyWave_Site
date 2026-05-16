# Mobile QA Matrix — MyWaveWake

**Фаза:** Operational Maturity · Stabilization execution  
**Baseline:** runtime `3de56f8c` (FROZEN) · frontend `48dc9c64`  
**Production URL:** https://mywavewake.ru  
**Active run:** [MOBILE_QA_RUN_2026-05-15.md](MOBILE_QA_RUN_2026-05-15.md) — **PENDING** (device run required)  
**Printable checklist:** [MANUAL_DEVICE_QA_CHECKLIST.md](MANUAL_DEVICE_QA_CHECKLIST.md)  
**GM brief:** [TEAM_STATUS_2026-05-17.md](../ops/TEAM_STATUS_2026-05-17.md)  
**Blocking:** governance-incomplete until 4× PASS + sign-off YES  
**Screenshots:** [screenshots/2026-05-15/](screenshots/2026-05-15/)

Матрица обязательна перед UX-deploy. Без PASS → deploy **governance-incomplete**.  
Gate: [RELEASE_GATE_CHECKLIST.md](../deployment/RELEASE_GATE_CHECKLIST.md)

---

## Как заполнять

| Колонка | Значение |
|---------|----------|
| **Result** | `PASS` / `FAIL` / `SKIP` / `N/A` |
| **Screenshot** | путь в `docs/qa/screenshots/YYYY-MM-DD/` или ссылка |
| **Notes** | баг, viewport, версия CSS (`?v=`), commit hash |

После deploy frontend: hard refresh / инкогнито; проверить `mobile-home.css?v=3` в Network.

**Не блокирует UX-only deploy:** backend/runtime (если не менялся).

---

## Минимальные платформы

| ID | Device | Browser | Viewport (ориентир) |
|----|--------|---------|---------------------|
| A1 | Android phone | Chrome | 360×800, 390×844 |
| A2 | Android phone | Yandex Browser | 360×800 |
| I1 | iPhone | Safari | 390×844, safe-area |
| T1 | Tablet | Chrome / Safari | 768×1024, 820×1180 |

---

## Матрица проверок

### A1 — Android Chrome

| Section | Result | Screenshot | Notes |
|---------|--------|------------|-------|
| Hero | | | compact, нет giant whitespace |
| Services carousel | | | swipe, snap, нет обрезки |
| Contacts | | | форма, поля, клавиатура |
| Chat button | | | не перекрывает CTA |
| Reviews | | | аватары, lazy/eager |
| Checklist | | | `/projects/checklist-org` |
| Booking modal | | | слоты, дата, закрытие |
| Blog | | | `/blog` list, карточки |
| Navigation | | | menu, anchor scroll |
| Footer | | | links, safe-area bottom |

### A2 — Android Yandex Browser

| Section | Result | Screenshot | Notes |
|---------|--------|------------|-------|
| Hero | | | |
| Services carousel | | | |
| Contacts | | | |
| Chat button | | | |
| Reviews | | | |
| Checklist | | | |
| Booking modal | | | |
| Blog | | | |
| Navigation | | | |
| Footer | | | |

### I1 — iPhone Safari

| Section | Result | Screenshot | Notes |
|---------|--------|------------|-------|
| Hero | | | safe-area top |
| Services carousel | | | momentum scroll |
| Contacts | | | input zoom ≤16px font |
| Chat button | | | home indicator offset |
| Reviews | | | |
| Checklist | | | |
| Booking modal | | | |
| Blog | | | |
| Navigation | | | |
| Footer | | | safe-area bottom |

### T1 — Tablet

| Section | Result | Screenshot | Notes |
|---------|--------|------------|-------|
| Hero | | | |
| Services carousel | | | |
| Contacts | | | |
| Chat button | | | |
| Reviews | | | |
| Checklist | | | |
| Booking modal | | | |
| Blog | | | |
| Navigation | | | |
| Footer | | | |

---

## Глобальные критерии (все платформы)

| Критерий | PASS если |
|----------|-----------|
| Horizontal scroll | отсутствует на главной и checklist |
| Touch targets | интерактивные элементы ≥ 44×44px |
| Typography | заголовки/текст читаемы без zoom |
| Spacing | нет «пустых полей» между hero и следующей секцией |
| Images | не растянуты, не обрезаны критично |
| Forms | labels видны, submit доступен |
| Performance | первая отрисовка без заметного layout shift |

---

## Связанные артефакты

| Документ | Назначение |
|----------|------------|
| [FRONTEND_POLISH_PHASE.md](../deployment/FRONTEND_POLISH_PHASE.md) | P1 UX scope, CSS paths |
| [RELEASE_GATE_CHECKLIST.md](../deployment/RELEASE_GATE_CHECKLIST.md) | gate перед prod deploy |
| [PRODUCTION_INCIDENT_POLICY.md](../ops/PRODUCTION_INCIDENT_POLICY.md) | при FAIL на prod после deploy |

## История прогонов

| Дата | Commit | Tester | Summary |
|------|--------|--------|---------|
| 2026-05-15 | `48dc9c64` | agent+owner | Automated pre-check PASS; prod HTML still `?v=2` — [MOBILE_QA_AUTOMATED_PRECHECK_2026-05-15.md](MOBILE_QA_AUTOMATED_PRECHECK_2026-05-15.md); device QA PENDING |

## Overall sign-off (2026-05-15)

| Field | Value |
|-------|-------|
| Overall | **PENDING** |
| Release gate ready | **NO** |
| Blocker | Real device QA + screenshots required |
