# Owner — диск prod (диагностика → safe clean)

**Сервер:** 4169037-ep26382  
**Статус:** CLOSED 2026-07-29 · было ~89% (5.7G) → **71% (15G free)**  
**Цель:** место без поломки Site / bot / Camp / ai-team docker  

**Сделано:**
- journal vacuum ~200M  
- `prometheus_multiproc` clean + site restart  
- удален `/opt/bot3/parser-new-bot.pre-git.20260717_013426` (~5.2G)  
- удален `/var/backups/mywave/20260707-1157` (~2.4G), оставлен `20260707-1444`  
- `docker builder prune -af` (~1.7G)  
- `docker image prune -af` (alpine dangling)  

**Живое (не трогать):**
- `/var/www/mywave` · `/opt/mywave-bot` · `/opt/bot3/parser-new-bot`  
- docker ai-team: `app` / `ollama` / `molt` / `postgres` + **volumes**  
- `mywave-node` · `mywave-staging`  

**Sanity PASS:** site/bot/node/parser active · health ok · blog 200  

---

## Если снова >85%

```bash
df -h /
sudo du -xh /opt/bot3/parser-new-bot/downloads --max-depth=1 | sort -h | tail -10
sudo docker system df
# downloads Parser — только после GO и сверки с Parser-командой
# docker volume prune — НЕ без GO
```
