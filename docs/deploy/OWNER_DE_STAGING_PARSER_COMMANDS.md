# Owner — D+E результат (2026-07-29)

## D — staging: STOP+disable (KEEP tree)

| Факт | Значение |
|------|----------|
| Ports | `:5000` site · `:5001` node · `:5002` staging |
| Local health | HTTP 200, `status=degraded` (optional AI/sentry) |
| Public DNS | **NXDOMAIN** `staging.mywavewake.ru` |
| Nginx | vhost есть → `:5002`, но hostname не резолвится |
| Journal | только наши `/health` curl — нет боевого трафика |
| Disk tree | `/var/www/mywave-staging` ~1.9G (**не удалять**) |

**Решение:** `stop` + `disable` unit → освободить RAM. Дерево и nginx config оставить (на случай будущего E2E + починки DNS).

## E — parser downloads: purge HOLD

Дубли `IMG_* (N).*` — только замер; `rm` после Parser GO.

Disk overall: **71% / 15G free** — ок.
