# GM Status Board — MyWave Site + Tour Camp

**Обновлено:** 2026-07-11  
**Owner:** Yaroslav  
**Критический путь:** Tour Camp API deploy → Gate → Site Camp deploy

---

## Сводка (одна строка)

**Site prod OK на `eab7eb98` (Online Coaching). Camp STOP. Блокер — Tour: Docker build preflight.**

---

## Матрица команд

| Команда | Сейчас | Следующий шаг | Блокер |
|---------|--------|---------------|--------|
| **Tour** | Deploy Camp API упал на CI | Fix Dockerfile + PR #5 merge + green workflow | `pnpm --filter api build` без `@mywave/shared-types`, `@mywave/explore-links` |
| **Site (код)** | PR #98/#99 в `main`, prod не тянем | Standby до gate | Tour endpoint |
| **Git** | Site `main` = `cdb4e59f` | Не трогать prod pull | Owner GO |
| **Owner** | Мониторинг prod | Health + gate checklist | — |

---

## SHA-реестр

| Артефакт | SHA |
|----------|-----|
| Site `origin/main` | `cdb4e59f248518575d1b275d1b0f7508f964d0b9` |
| Camp contract (#98) | `75c0c792bcf3ee44b7919f29f27dcc47f4e3d96c` |
| Booking hotfix (#99) | в `cdb4e59f` (на prod **нет**) |
| **Site production** | `eab7eb9859054024275df8ae8a5115e1d6830c89` |

---

## Gate Site deploy (все 8 пунктов)

- [ ] 1. Tour PR #5 merge
- [ ] 2. Successful **Deploy Camp API**
- [ ] 3. `/api/v1/camps` → 200 + `{ items, next_offset }`
- [ ] 4. Bearer auth OK
- [ ] 5. `/tmp/mywave-camps-sample.json` с Site
- [ ] 6. Token rotation + private handoff → Site `.env`
- [ ] 7. Sample summary от Tour
- [ ] 8. Owner GO → `docs/deploy/CAMP_DEPLOY.md` § Production deploy

---

## Site production STOP (жёстко)

- без `git pull origin main`
- без `flask db upgrade` (Camp)
- без `run_camp_sync.py`
- без camp cron
- `CAMP_PUBLIC_ENABLED=0`

---

## Tour VPS инварианты (пока CI red)

- Running API **без** `/api/v1/camps`
- `/root/CAMP_API_TOKEN.current` **не должен существовать**
- Token rotation **не выполнялась**

---

## Опциональное решение Owner (вне Camp gate)

Hotfix #99 (booking `calendarLocation`) в `main`, но **не на prod**.  
Если баг booking критичен для пользователей — отдельный owner GO на **изолированный** deploy только #99 **без** Camp env/миграций. Иначе ждём общий gate.

---

## Ссылки

- Site Camp runbook: `docs/deploy/CAMP_DEPLOY.md`
- Site OC runbook: `docs/deploy/ONLINE_COACHING_PHASE2_SERVER.md`
- Preflight script: `scripts/check_tour_camp_api.py`
