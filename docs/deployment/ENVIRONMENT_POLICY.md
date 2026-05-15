# Environment Policy — MyWaveWake

**Production:** https://mywavewake.ru (frozen runtime baseline `3de56f8c`)  
**Governance:** [PRODUCTION_GOVERNANCE.md](../PRODUCTION_GOVERNANCE.md)

---

## Environments

| Env | Purpose | Base URL (example) | Runtime changes |
|-----|---------|-------------------|-----------------|
| **local** | dev | `http://127.0.0.1:5000` | разрешены |
| **staging** | smoke / pre-prod validation | TBD (отдельный host) | по approval, не prod data |
| **production** | live traffic | `https://mywavewake.ru` | **frozen** — governance only |

---

## Allowed services by environment

| Service | local | staging | production |
|---------|-------|---------|------------|
| Flask/Gunicorn | ✓ | ✓ | ✓ (frozen config) |
| Redis | optional | ✓ | ✓ |
| Socket.IO | ✓ | ✓ | ✓ |
| Node proxy | optional | ✓ | ✓ |
| Google APIs | test SA / mock | test SA | prod SA (не в git) |
| Telegram bots | dev bot | staging bot | prod bot |

---

## Required smoke

| Env | Before deploy | After deploy |
|-----|---------------|--------------|
| local | `pytest tests/unit` (если код) | manual |
| staging | `production_smoke.sh` на staging URL | обязательно |
| production | gate + smoke на staging или last-known-good | `production_smoke.sh` обязательно |

```bash
MYWAVE_BASE_URL=https://mywavewake.ru bash scripts/production_smoke.sh
```

---

## Deploy permissions

| Env | Кто может deploy | Условия |
|-----|------------------|---------|
| local | любой dev | — |
| staging | release manager, ops | release type classified |
| production | release manager | [RELEASE_GATE_CHECKLIST.md](RELEASE_GATE_CHECKLIST.md) PASS |

Runtime production deploy: **только** runtime owner + explicit approval + 5-point change control.

---

## Environment restrictions

| Правило | local | staging | production |
|---------|-------|---------|------------|
| Secrets in git | **запрещено** | **запрещено** | **запрещено** |
| `.env` в repo | только `.env.example` | — | — |
| Direct hotfix без smoke | допустим локально | запрещено | **запрещено** |
| Mixed runtime+UX deploy | — | избегать | **запрещено** без approval |
| Debug / FLASK_DEBUG | ✓ | controlled | **запрещено** |
| PII в логах | минимизировать | минимизировать | **запрещено** |

---

## Config source of truth

| Файл | Назначение |
|------|------------|
| `.env.example` | шаблон переменных (без secrets) |
| `/var/www/mywave/.env` | production secrets (server only) |
| `configs/service_account.json` | Google SA (server only, не в git) |

---

## Связанные документы

- [RUNTIME_GOVERNANCE.md](RUNTIME_GOVERNANCE.md)  
- [RELEASE_TYPES.md](RELEASE_TYPES.md)  
- [TIMEWEB_PRODUCTION_RUNBOOK.md](TIMEWEB_PRODUCTION_RUNBOOK.md)
