# MyWaveWake — фаза Frontend Polish + Hardening

**Дата фиксации:** 2026-05  
**Production runtime baseline (заморожен):** `3de56f8c9316158aa992cfb7e74f0330eec0171c`

Критическая фаза backend instability **завершена**. Backend operational:

- Flask/Gunicorn, Redis, Google Services, Booking slots, Node proxy
- systemd, Nginx, Socket.IO, `/health`, Google Sheets

---

## Главное правило: BACKEND ЗАМОРОЖЕН

Backend **не трогаем** без:

1. отдельного issue  
2. описания риска  
3. rollback plan  
4. smoke strategy  
5. production justification  

### Под запретом без согласования

- Flask bootstrap (`create_app`, extensions init)
- Gunicorn / worker wiring
- SQLAlchemy init (`app.database.models.db`)
- Redis / Flask-Limiter wiring
- Socket.IO runtime
- booking API (`calendar_routes`, slots)
- Google services init
- env loading
- health routing (`app/routes/health.py`)
- runtime patches (DNS, SSL)
- WebSocket architecture

Backend = **production runtime foundation**.

---

## Текущая фаза проекта

| Приоритет | Область |
|-----------|---------|
| 1 | UX |
| 2 | Mobile |
| 3 | Content (Sheets / parser visibility) |
| 4 | Monitoring |
| 5 | Security hardening |

**Не делаем:** новые backend features, runtime refactor, async rewrites, migration chaos, архитектурные эксперименты.

---

## P1 — Mobile UX polish

**Артефакт:** [`static/css/mobile-home.css`](../../static/css/mobile-home.css) (v3, cache `?v=3` в `base.html`)  
**Дополнительно:** mobile block в [`static/css/checklist.css`](../../static/css/checklist.css)

### QA matrix (обязательно перед «done»)

| Платформа | Браузер |
|-----------|---------|
| Android | Chrome |
| Android | Yandex Browser |
| iOS | Safari |
| Tablet | 768–1024px viewport |

### Контрольные точки

- [ ] Hero compact, нет giant whitespace  
- [ ] Swipe-карусели, scroll-snap  
- [ ] Карточки не режутся, нет horizontal scroll  
- [ ] Typography читаема, touch targets ≥ 44px  
- [ ] Формы и контакты не ломаются  
- [ ] safe-area (iPhone/Android)  
- [ ] Chat button не перекрывает CTA  
- [ ] Не трогать backend ради UX  

**Deploy frontend-only:** `git pull` + hard refresh / `?v=3`; restart Gunicorn не обязателен для CSS.

---

## P1 — Blog content pipeline

**Routing стабилен** (HTTP 200). Проблема: **нет visible content** на витрине.

**Не менять:** blog routes, runtime, architecture.

**Диагностика:** [`BLOG_CONTENT_VISIBILITY.md`](BLOG_CONTENT_VISIBILITY.md)

- `raw_feed` statuses: `READY_TO_PUBLISH` / `PUBLISHED`  
- slug, parser sync, cache TTL / invalidate  
- `GET /api/blog/posts` vs `?db_only=1`  

---

## P1 — Checklist visuals

Placeholder webp в `static/images/Project/Cards/checklist/`.

**Нужно от дизайна:** финальные иллюстрации, единый art-direction, optimized webp.

**Не менять:** asset routing, template structure, `checklist.js` rendering logic.

---

## P1 — Reviews / static media

- responsive avatars, static cache, nginx `/static/`  
- eager loading на главной (см. `index.html`)  
- проверка 200 на `/static/images/students/*.jpg`  

---

## P2 — Hardening

См. [`TIMEWEB_PRODUCTION_RUNBOOK.md`](TIMEWEB_PRODUCTION_RUNBOOK.md):

- fail2ban, UFW, logrotate, backup cron  
- Redis persistence, gzip/cache, certbot renew  
- nginx rate limiting, security headers  

---

## P2 — Observability

- [`scripts/production_smoke.sh`](../../scripts/production_smoke.sh)  
- [`scripts/healthcheck.sh`](../../scripts/healthcheck.sh)  
- health watchdog, Telegram alerts, disk/log monitoring  

---

## P2 — CI/CD

- GitHub Actions status  
- deploy rollback: [`POST_DEPLOY_ROLLBACK.md`](POST_DEPLOY_ROLLBACK.md)  
- release tagging, env separation, secrets hygiene  

---

## Обязательные правила работы

1. Backend runtime — только с approval.  
2. Frontend — mobile-first.  
3. Production правка → rollback path.  
4. Нет hotfix в prod без smoke.  
5. Secrets не в git.  
6. Stable API contracts не ломать.  
7. Socket.IO / Google / booking — не трогать.  
8. Изменения — в docs/runbooks.  

---

## Цель фазы

- visually polished  
- mobile-ready  
- production hardened  
- observable  
- demo / investor ready  

**После stabilization:** SEO, parser automation, sponsor platform, AI orchestration, tourism ecosystem, advanced analytics.

---

## Rollback

| Тип | Действие |
|-----|----------|
| Frontend | `git revert <ux-commit>` + nginx reload / cache bust |
| Backend | только на baseline `3de56f8c` + issue; `systemctl restart mywave-site` |

## История release commits

| Commit | Назначение |
|--------|------------|
| `68b46537` | Timeweb prod baseline |
| `8ee0ca40` | Post-deploy pack + mobile v1 |
| `3de56f8c` | **Frozen runtime** — blog/health P0 |
