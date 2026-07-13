# SITE — план завершения mywavewake.ru (S1–S11)

**Production pin (текущий):** `d9b68b75c81fd256da13fcde5756d17594bb56fa`  
**Production branch:** `deploy/booking-hotfix-99`  
**Rollback SHA:** `eab7eb9859054024275df8ae8a5115e1d6830c89` (pre-hotfix #99)  
**Health:** PASS — hotfix #99 **не передеплоивать**

Не использовать `git pull origin main` до консолидации release-веток.

## Release map

| Release | Branch (target) | Base SHA | Status | Scope |
|---|---|---|---|---|
| **S1** | `release/s1-oc-copy-pricing` | `d9b68b75` | In PR | OC copy + «12 000 ₽ / месяц», oc-film tips |
| **S2** | `release/s2-oc-mobile-polish` | S1 tip | Planned | Mobile UX, RU statuses, remove MAX/WhatsApp from OC UI |
| **S3** | `release/s3-calendar-ics-ux` | S1 or S2 tip | Planned | Calendar SUMMARY/LOCATION/ICS, boat/gym human titles |
| **S4** | `release/booking-yclients-boat-v1` | `d9b68b75` | Scaffold exists (`efdcb2da`) | Cherry-pick boat/YClients only; flags OFF |
| **S5** | — | S4 | Blocked | YClients read-only staging (needs credentials) |
| **S6** | — | S5 | Blocked | YClients controlled write E2E |
| **S7** | — | — | Planned | Blog editorial standard + Blog v2 contract |
| **S8** | — | — | Planned | Blog video rendering + CSP |
| **S9** | — | — | Planned | Site Admin for Blog |
| **S10** | — | — | **STOP** | Camp — Tour API `/api/v1/camps` 404; `CAMP_PUBLIC_ENABLED=0` |
| **S11** | — | — | Planned | Final Site audit |

## Business rules (canonical)

- **Эффективный месяц:** 12 000 ₽ / **месяц** (не / сет)
- **YClients:** только `service_type=boat`; gym и остальное — Site/TGbotAdmin
- **Катер:** 1 клиент / 30-min slot; multi-set duration; YClients = SoT → GCal mirror → Sheets audit
- **Зал:** 90 min, max 4 clients; Site/TGbotAdmin
- **MAX/WhatsApp:** исключены из release waves S2+ (удаление из OC UI в S2)

## Architecture — boat booking (S4+)

```
Site / TGbotAdmin
       ↓
единый YClients adapter
       ↓
YClients (source of truth, boat only)
       ↓
Google Calendar mirror
       ↓
Sheets audit/log
       ↓
Telegram notification
```

## Cross-team contracts

| Team | Responsibility |
|---|---|
| **TGbotAdmin** | Единый booking contract; не дублировать YClients write |
| **MyWaveTour** | Camp API only; Site не управляет Tour DB |
| **ParserNews** | Upstream normalized content; Site = render + publication workflow |

## Production deploy template

| Field | Value |
|---|---|
| Проект | Site MyWave |
| Сервер | `4169037-ep26382` / `62.113.42.227` |
| cwd | `/var/www/mywave` |
| Restart OK | `mywave-site.service` |
| Do NOT touch | `mywave-node`, `mywave-telegram-bot`, TGbotAdmin |
| Ops untracked | `scripts/check_telegram_bot.sh` — не в релизах |

## Key SHAs

| SHA | Role |
|---|---|
| `eab7eb98` | Rollback before hotfix #99 code pin |
| `d9b68b75` | **Current production** / S1–S4 base |
| `efdcb2da` | seasonal + YClients scaffold (cherry-pick source for S4) |
| `cdb4e59f` | `origin/main` (includes Camp — not for prod deploy yet) |

## S1 deliverable

See `docs/deploy/RELEASE_S1_OC_COPY_PRICING.md`.

## Blockers

1. **Camp S10:** Tour Camp API not ready (404).
2. **YClients S5–S6:** Real credentials and API contract confirmation required.
3. **Owner GO** required for any production deploy.
