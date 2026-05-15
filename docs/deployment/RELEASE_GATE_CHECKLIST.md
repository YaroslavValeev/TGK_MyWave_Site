# Release Gate Checklist — MyWaveWake

**Обязателен перед любым production deploy.**

Фаза: Production Stabilization + QA Discipline  
**Production:** https://mywavewake.ru  

| Baseline | Commit | Статус |
|----------|--------|--------|
| Runtime Foundation | `3de56f8c` | FROZEN |
| Frontend/docs | `48dc9c64` | ACTIVE |
| QA/Ops governance | `0a2a0e1a` | ACTIVE |
| Production state/docs | `94fbc211` | ACTIVE |
| Governance index | `4d1ded82` | ACTIVE |
| Phase transition | `56b98c49` | ACTIVE |

**Платформа:** production-governed · **ОДИН DEPLOY = ОДИН RELEASE TYPE** — [RELEASE_TYPES.md](RELEASE_TYPES.md) · [PRODUCTION_GOVERNANCE.md](../PRODUCTION_GOVERNANCE.md) · runtime: [RUNTIME_GOVERNANCE.md](RUNTIME_GOVERNANCE.md)

---

## 1. Scope classification

Отметьте **один** основной слой изменения:

| Слой | Допустимо без runtime approval | Требует approval |
|------|-------------------------------|------------------|
| **Runtime Foundation** | — | всё (issue + rollback + smoke + justification) |
| **Frontend UX** | CSS, templates (без API), images | если затрагивает JS API contracts |
| **Content Pipeline** | Sheets statuses, parser, slug | blog routing / store code |
| **Ops/Observability** | nginx, fail2ban, cron, scripts | Gunicorn, Redis, Flask init |

- [ ] Слой определён: _______________
- [ ] Runtime **не** затронут (или есть approved issue #____)

---

## 2. Pre-deploy (локально / CI)

| # | Check | PASS |
|---|-------|------|
| 2.1 | `git log -1` — commit осознан | [ ] |
| 2.2 | Нет secrets в diff (`.env`, keys, SA json) | [ ] |
| 2.3 | Backend frozen: нет правок `app/__init__.py`, health, booking, Redis, Socket.IO | [ ] |
| 2.4 | Unit tests (если менялся код): `pytest tests/unit -q` | [ ] |
| 2.5 | Rollback commit записан: `________________` | [ ] |

---

## 3. Smoke (обязательно)

На **целевом** URL (prod или pre-prod):

```bash
MYWAVE_BASE_URL=https://mywavewake.ru bash scripts/production_smoke.sh
```

| # | Check | PASS |
|---|-------|------|
| 3.1 | home → 200 | [ ] |
| 3.2 | /blog → 200 | [ ] |
| 3.3 | /health → 200 (degraded optional OK) | [ ] |
| 3.4 | /health/live → 200 | [ ] |
| 3.5 | /node-chat/health → 200 | [ ] |
| 3.6 | static review image → 200 | [ ] |
| 3.7 | slots API → 200 | [ ] |
| 3.8 | Smoke script exit 0 | [ ] |

**Health policy:** `unhealthy` только при падении **core** (database). Redis/Sentry/Google optional → `degraded` + HTTP 200.

---

## 4. Mobile QA (обязательно для Frontend UX)

Заполнена матрица: [MOBILE_QA_MATRIX.md](../qa/MOBILE_QA_MATRIX.md)

| # | Check | PASS |
|---|-------|------|
| 4.1 | Android Chrome — затронутые секции PASS | [ ] |
| 4.2 | Android Yandex — затронутые секции PASS | [ ] |
| 4.3 | iPhone Safari — затронутые секции PASS | [ ] |
| 4.4 | Tablet — затронутые секции PASS | [ ] |
| 4.5 | Нет horizontal scroll на главной | [ ] |
| 4.6 | Screenshots приложены (путь/ссылка) | [ ] |

**N/A:** если deploy только Ops/Content без UI — явно указать в release notes.

---

## 5. Infrastructure sanity

| # | Check | PASS |
|---|-------|------|
| 5.1 | Redis: `redis-cli ping` → PONG (на сервере) | [ ] |
| 5.2 | SSL: cert valid, `curl -I https://mywavewake.ru` | [ ] |
| 5.3 | Static: sample `/static/css/mobile-home.css?v=3` → 200 | [ ] |
| 5.4 | Nginx: `sudo nginx -t` | [ ] |
| 5.5 | systemd: `mywave-site`, `mywave-node` active | [ ] |

---

## 6. Rollback confirmed

| # | Check | PASS |
|---|-------|------|
| 6.1 | PREV commit: `________________` | [ ] |
| 6.2 | [POST_DEPLOY_ROLLBACK.md](POST_DEPLOY_ROLLBACK.md) прочитан | [ ] |
| 6.3 | Runtime rollback → `3de56f8c` (если трогали runtime) | [ ] |
| 6.4 | Frontend rollback → предыдущий UX commit | [ ] |
| 6.5 | Backup свежий (< 24h) при ops-изменениях | [ ] |

---

## 7. Deploy execution

```bash
cd /var/www/mywave
git fetch origin && git checkout <RELEASE_COMMIT>
# runtime-only:
# /var/www/mywave/venv/bin/pip install -r requirements.txt
# sudo systemctl restart mywave-site  # только если менялся backend
sudo nginx -t && sudo systemctl reload nginx
bash scripts/production_smoke.sh
```

| # | Check | PASS |
|---|-------|------|
| 7.1 | Deploy выполнен | [ ] |
| 7.2 | Post-deploy smoke PASS | [ ] |
| 7.3 | Release tag / commit зафиксирован в runbook | [ ] |

---

## 8. Sign-off

| Роль | Имя | Дата | Commit |
|------|-----|------|--------|
| Deployer | | | |
| QA (mobile, если UX) | | | |

**Gate status:** [ ] APPROVED FOR PROD  [ ] BLOCKED

При BLOCKED — см. [PRODUCTION_INCIDENT_POLICY.md](../ops/PRODUCTION_INCIDENT_POLICY.md).

---

## Quick reference

| Артефакт | Путь |
|----------|------|
| Mobile QA | `docs/qa/MOBILE_QA_MATRIX.md` |
| Incidents | `docs/ops/PRODUCTION_INCIDENT_POLICY.md` |
| Rollback | `docs/deployment/POST_DEPLOY_ROLLBACK.md` |
| Smoke | `scripts/production_smoke.sh` |
| Phase rules | `docs/deployment/FRONTEND_POLISH_PHASE.md` |
