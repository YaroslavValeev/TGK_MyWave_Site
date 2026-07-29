# Owner — следующий этап после YClients (Blog → S11)

**Дата:** 2026-07-29  
**YClients S5–S10:** CLOSED  
**Blog B2 SEO:** CLOSED (`c70b13f6`)  
**Blog B1 + B3:** CLOSED (`d1fe85ed`) — см. `docs/deploy/OWNER_B1_B3_COMMANDS.md`  
**Camp:** HOLD  

---

## Быстрый health

```bash
systemctl is-active mywave-site mywave-telegram-bot
cd /var/www/mywave && git log -1 --oneline
# ожидаемо: d1fe85ed …
curl -fsS https://mywavewake.ru/health
```

---

## Статус волн

| # | Scope | Статус |
|---|-------|--------|
| YClients S5–S10 | boat gateway | **CLOSED** |
| Blog diagnose | /blog + API | **PASS** |
| B2 | home preview, search, SEO | **CLOSED** |
| B1 | editorial + title/slug hygiene | **CLOSED** |
| B3 | video CSP allowlist | **CLOSED** |
| B4 | Admin Blog write | pending GO |
| S11 | Final audit | after B4 / GO |
| Camp | Tour + cron | **HOLD** |

---

## Не делать без GO

- Camp import/cron
- `YCLIENTS_WRITE_ENABLED=0` без причины
- Push force / restart `mywave-node`
- Rewrite старых slug в Sheets без плана редиректов
