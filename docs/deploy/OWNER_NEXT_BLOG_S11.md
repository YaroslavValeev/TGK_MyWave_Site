# Owner — следующий этап после YClients (Blog → S11)

**Дата:** 2026-07-29  
**YClients S5–S10:** CLOSED на prod  
**Camp:** hold (Tour отладка; cron OFF; public может быть ON с пустой витриной)

---

## Быстрый health (Site + Bot)

```bash
systemctl is-active mywave-site mywave-telegram-bot
cd /var/www/mywave && git branch --show-current && git log -1 --oneline
cd /opt/mywave-bot && git branch --show-current && git log -1 --oneline
curl -fsS https://mywavewake.ru/health
curl -sS "https://mywavewake.ru/api/calendar/slots/$(date -d '+3 days' +%F)?service=boat" | python3 -m json.tool | head -20
```

---

## Blog — диагностика (шаг 1)

```bash
cd /var/www/mywave
source venv/bin/activate
set -a; source .env; set +a

# публичная витрина
curl -sS -o /dev/null -w "%{http_code}\n" https://mywavewake.ru/blog
curl -sS "https://mywavewake.ru/api/blog/latest" | python3 -m json.tool | head -40
curl -sS "https://mywavewake.ru/api/blog/posts?limit=5" | python3 -m json.tool | head -60

# канон/доки (локально на сервере после pull)
ls docs/BLOG_CONTRACT_v1.md docs/BLOG_EDITORIAL_CHECKLIST.md docs/migration/BLOG_BACKLOG_PLAN.md
```

**PASS:** `/blog` = 200, latest/posts JSON без 500.

---

## Blog — волны (после diagnose)

| # | Scope | Док |
|---|-------|-----|
| B1 | Editorial checklist + ParserNews contract (процесс) | `docs/BLOG_EDITORIAL_CHECKLIST.md`, `docs/BLOG_CONTRACT_v1.md` |
| B2 | Backlog UX/SEO (latest на главной, поиск, категории) | `docs/migration/BLOG_BACKLOG_PLAN.md` |
| B3 | Video + CSP | `docs/architecture/BLOG_RUNTIME_CANON.md` |
| B4 | Admin Blog write workflow | Site Admin |
| S11 | Final Site audit | после B1–B4 |

---

## Не делать без GO

- Camp import/cron
- `YCLIENTS_WRITE_ENABLED=0` rollback без причины
- Push force на main
- Restart `mywave-node`

---

## Опциональный мелкий техдолг YClients (не блокер)

После gateway reschedule бот иногда логирует `Invalid sequence value` на GCal — SoT уже обновлён mirror’ом; двойной update в боте можно убрать отдельным мелким PR.
