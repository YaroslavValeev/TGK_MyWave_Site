# Owner — статус волн (обновлено 2026-07-31)

## CLOSED
- **YClients S5–S10** · **slot30/amount** (`c7729014`)
- **YC human comment** (`68ea9666`) — prod deployed · `через сайт` / `через ТГ`
- **Blog B1–B4.2 / S11**
- **Camp** — published:1 + archived:3 · cron · `/camps` 200
- **D staging** — unit stop+disable · nginx symlink removed · **tree kept**
- **E parser downloads purge** — 4.3G→920M
- **Tour TG callback smoke** — PASS · autopublish **HOLD** (команда Tour)
- **YC partner text 01.08** — SENT

## OPEN / чужие репо
1. YC UI правка 01.08 (партнёр): end 16:30 · qty 3  
2. Parser: не минтить `(N)` при re-download  
3. Tour autopublish GO  
4. Optional: удалить `/var/www/mywave-staging` (~1.9G) после отдельного ACK  

## Site local follow-up
- `migrate-blog` CLI registration в `create_app` (не запускать на prod без GO)
- Runbook: `OWNER_REMAINING_OPS_COMMANDS.md`
