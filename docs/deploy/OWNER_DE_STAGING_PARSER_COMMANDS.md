# Owner — D+E CLOSED (2026-07-29)

## D — staging STOP+disable · PASS

| Check | Result |
|-------|--------|
| `mywave-staging` | `inactive` / `disabled` |
| `:5002` | closed |
| site / telegram-bot / node / parser | active |
| health / blog | ok / 200 |
| Tree `/var/www/mywave-staging` | **kept** (~1.9G) |
| Nginx vhost | **disabled** 2026-07-29: removed `sites-enabled` symlink; `sites-available` kept |

**Rollback unit:** `sudo systemctl enable --now mywave-staging`  
**Rollback vhost:** `sudo ln -s /etc/nginx/sites-available/staging.mywavewake.ru /etc/nginx/sites-enabled/staging.mywavewake.ru && sudo nginx -t && sudo systemctl reload nginx`

## E — downloads purge · CLOSED PASS (2026-07-29 20:18)

| Metric | Before → After |
|--------|----------------|
| `downloads` | **4.3G → 920M** |
| zero-byte deleted | **1770** |
| dup `* (N).*` deleted | **909 · ~3.33G** |
| Disk `/` | **71%/15G → 64%/19G** |
| services / health | all active · `ok` |
| Logs | `/root/parser_dl_cleanup_20260729_201829.{zero,dups}` |

**Note:** ранее «2398» включало zero + dups; sized-dups оказались **909**.  
**Purge runbook:** `docs/deploy/OWNER_PARSER_DL_CLEANUP_COMMANDS.md`

## Текст Parser (после purge)

> На prod сняли дубли `IMG_xxxx (1).MOV` (~3.3G). Оригиналы без `(N)` оставили.  
> Просьба: в коде сохранения media не создавать `(1)/(2)` при повторном скачивании — overwrite или skip по checksum.
