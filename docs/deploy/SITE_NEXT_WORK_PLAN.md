# SITE — NEXT WORK PLAN (после S1+P0)

**Дата фиксации:** 2026-07-15  
**Production HEAD:** `b029c21a6876cb8a61b8d8c9b17473dd26ac4bda`  
**Branch:** `release/s1-oc-copy-pricing`  
**Rollback SHA:** `d9b68b75c81fd256da13fcde5756d17594bb56fa`  
**Emergency stash:** `stash@{0}` (`emergency-ratelimit-20260715-112541`) — **не pop**

Не использовать `git pull origin main` на production.

---

## Статус S1–S11

| Release | Status | Команда / зависимость |
|---|---|---|
| **S1** OC copy/pricing | **DONE on prod** | Site |
| **P0** rate-limit | **DONE on prod** | Site |
| Hotfix #99 booking JS | **DONE** (не передеплоивать) | Site |
| **S2** OC mobile polish + RU statuses | **NEXT** | Site only |
| **S3** Calendar / ICS UX | Planned | Site (+ optional TGbotAdmin contract notes) |
| **S4** YClients boat scaffold (flags OFF) | Repo scaffold / audit | Site ↔ **TGbotAdmin** |
| **S5** YClients read-only | **BLOCKED** | Site + Owner credentials + YClients contract |
| **S6** YClients controlled write | **BLOCKED** | после S5 PASS |
| **S7** Blog editorial standard | Planned | Site ↔ **ParserNews** |
| **S8** Blog video + CSP | Planned | Site |
| **S9** Site Admin Blog | Planned | Site (не Tour/Parser admin) |
| **S10** Camp public | **STOP** | Site ↔ **MyWaveTour** (API 200/401) |
| **S11** Final audit | Last | Site + Owner |

---

## Взаимодействие с командами

### Site (мы)
- Owner product surface: mywavewake.ru
- Releases S2, S3, S4(repo), S7–S9, S11
- Не трогать: TGbotAdmin service, mywave-node, mywave-telegram-bot

### TGbotAdmin
- Единый booking contract
- YClients **только катер**, один adapter — без двойной записи Site+Bot
- Зал: остаётся Site/TGbotAdmin (не YClients)

### MyWaveTour
- Готовый Camp API: `GET /api/v1/camps`, Bearer, envelope
- До GO: `CAMP_PUBLIC_ENABLED=0`, без sync/cron на Site

### ParserNews
- Upstream `raw_feed` / media fields
- Site: render, preview, publish workflow (S7–S9)

---

## Порядок работ (канон)

1. **S2** — mobile OC, chat overlap, format cards, RU statuses  
2. **S3** — Calendar SUMMARY/LOCATION/ICS UX  
3. **S4** — `release/booking-yclients-boat-v1` от `b029c21a` / audited cherry-pick, flags OFF  
4. **S5→S6** — только после credentials + Owner GO  
5. **S7→S9** — Blog  
6. **S10** — только после Tour API PASS  
7. **S11** — audit

Anti-scope во всех waves: не тянуть Camp/YClients writes/Parser admin/MAX-WhatsApp roadmap.
