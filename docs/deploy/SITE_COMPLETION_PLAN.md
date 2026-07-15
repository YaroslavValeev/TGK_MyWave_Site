# SITE — план завершения mywavewake.ru (S1–S11)

**Production pin (текущий):** `77da818d203acb8df0cf75fdf4a43b016c424670`  
**Production branch:** `release/s3-admin-sections-fill`  
**Rollback SHA:** `c1ebacabe2b7e158f629bb6891362d8c6c6f5e94` (S2)  
**Health:** PASS — S1 + P0 + S2 + S3a admin fill **DEPLOYED** (2026-07-15)  
**Hotfix #99:** previously verified — не передеплоивать отдельно  
**Emergency stash:** keep; do **not** `stash pop`

Не использовать `git pull origin main` до консолидации release-веток.

## Release map

| Release | Branch (target) | Base SHA | Status | Scope |
|---|---|---|---|---|
| **S1** | `release/s1-oc-copy-pricing` | `d9b68b75` | **DONE on prod** | OC copy + «12 000 ₽ / месяц», oc-film tips |
| **P0** | (in S1 branch) | `d9b68b75` | **DONE on prod** | Remove global 200/day rate limit |
| **S2** | `release/s2-oc-mobile-polish` | `48700c5a` | **DONE on prod** | Mobile UX, RU statuses, chat overlap / format cards |
| **S3a** | `release/s3-admin-sections-fill` | `c1ebacab` | **DONE on prod** | Admin Blog/Events/Users/Settings + Camp UI fix |
| **S3** | `release/s3-calendar-ics-ux` | `77da818d` | **NEXT** | Calendar SUMMARY/LOCATION/ICS, boat/gym human titles |
| **S4** | `release/booking-yclients-boat-v1` | prod tip | Scaffold (`efdcb2da`) | Cherry-pick boat/YClients only; flags OFF |
| **S5** | — | S4 | Blocked | YClients read-only staging (needs credentials) |
| **S6** | — | S5 | Blocked | YClients controlled write E2E |
| **S7** | — | — | Planned | Blog editorial standard + Blog v2 contract |
| **S8** | — | — | Planned | Blog video rendering + CSP |
| **S9** | — | — | Planned | Site Admin Blog write workflow |
| **S10** | — | — | **STOP** | Camp — Tour API not GO; `CAMP_PUBLIC_ENABLED=0` |
| **S11** | — | — | Planned | Final Site audit |

## Business rules (canonical)

- **Эффективный месяц:** 12 000 ₽ / **месяц** (не / сет)
- **YClients:** только `service_type=boat`; gym и остальное — Site/TGbotAdmin
- **Катер:** 1 клиент / 30-min slot; multi-set duration; YClients = SoT → GCal mirror → Sheets audit
- **Зал:** 90 min, max 4 clients; Site/TGbotAdmin

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
| `d9b68b75` | Pre-S1 production / S1 rollback |
| `b029c21a` | **Current production** (S1 + P0) |
| `efdcb2da` | seasonal + YClients scaffold (cherry-pick source for S4) |
| `cdb4e59f` | `origin/main` (includes Camp — not for prod deploy yet) |

## S1 deliverable

See `docs/deploy/RELEASE_S1_OC_COPY_PRICING.md`.  
See also `docs/deploy/SITE_NEXT_WORK_PLAN.md`.

## Blockers

1. **Camp S10:** Tour Camp API not ready / no Owner GO.
2. **YClients S5–S6:** Real credentials and API contract confirmation required.
3. **Owner GO** required for any further production deploy (S2+).
