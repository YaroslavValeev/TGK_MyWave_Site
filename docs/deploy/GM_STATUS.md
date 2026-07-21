# GM Status Board — MyWave Site + Tour Camp

**Обновлено:** 2026-07-21  
**Owner:** Yaroslav  
**Критический путь:** закрыт (Site ↔ Tour Camp API production accepted)

---

## Сводка (одна строка)

**Camp showcase LIVE на Site prod `3e7a5bf6`. Tour API принят. Публично: только текущие/будущие + без synthetic/MVP.**

---

## Матрица команд

| Команда | Сейчас | Следующий шаг | Блокер |
|---------|--------|---------------|--------|
| **Tour** | Camp API production smoke PASS | Обратно совместимые изменения API + повторный list/detail smoke | — |
| **Site** | `/camps` + detail на prod | Мониторинг fallback-логов; ждать реальные будущие кемпы в Tour | — |
| **Git** | Site `main` = `3e7a5bf6` | Следующие фичи вне Camp | — |
| **Owner** | Интеграция принята обеими командами | Не включать camp cron / `run_camp_sync` без отдельного GO | — |

---

## SHA-реестр

| Артефакт | SHA |
|----------|-----|
| Site `origin/main` / **production** | `3e7a5bf69a9188d82f6edab8a87e35b6365fcd13` |
| Camp showcase release | PR [#108](https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/108) → merge `db7d3250` |
| Hide past camps | PR [#109](https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/109) |
| Hide synthetic/test | PR [#110](https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/110) → `3e7a5bf6` |

---

## Gate Site deploy — закрыт

- [x] Tour Camp API list/detail production OK  
- [x] Bearer auth OK  
- [x] Site `/camps` + detail smoke OK  
- [x] PR #108 → `main` → production  
- [x] Past camps hidden on Site  
- [x] Synthetic/MVP (`tour_camp_api_mvp_wakesurf_v1`) hidden on Site  
- [x] Tour письменно принял интеграцию  

---

## Production policy (актуально)

- `CAMP_MODULE_ENABLED=1`, `CAMP_PUBLIC_ENABLED=1`
- Витрина: только `end_date`/`start_date` ≥ сегодня; без MVP/smoke/synthetic
- Fallback detail→list оставлен как safety net; лог: `camp_detail_fallback_list`
- **Не включать** без отдельного owner GO: `run_camp_sync.py`, camp cron, `flask db upgrade` под Camp tables (если ещё не применяли осознанно)

---

## Ссылки

- Site Camp runbook: `docs/deploy/CAMP_DEPLOY.md`
- Preflight: `scripts/check_tour_camp_api.py`
