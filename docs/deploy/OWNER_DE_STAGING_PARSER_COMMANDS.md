# Owner — D+E CLOSED (2026-07-29)

## D — staging STOP+disable · PASS

| Check | Result |
|-------|--------|
| `mywave-staging` | `inactive` / `disabled` |
| `:5002` | closed |
| site / telegram-bot / node / parser | active |
| health / blog | ok / 200 |
| Tree `/var/www/mywave-staging` | **kept** (~1.9G) |
| Nginx vhost | kept (DNS NXDOMAIN) |

**Rollback:** `sudo systemctl enable --now mywave-staging`

## E — downloads diagnose · PASS / purge HOLD

| Metric | Value |
|--------|-------|
| `downloads` | **4.3G** |
| `review_media/` | 364K |
| dup-like `* (N).*` | **2398 files · ~3.33G** |
| Disk `/` | 71% · 15G free |

**Не удалять** без ACK Parser-команды.

Подозрение: `/opt/bot3/parser-new-bot` может быть symlink (`du /opt/bot3` = 4K). Проверка:

```bash
ls -la /opt/bot3
readlink -f /opt/bot3/parser-new-bot
```

## Текст Parser (копипаст)

> На prod `downloads` ≈ 4.3G, из них ~3.33G в дублях вида `IMG_xxxx (1).MOV`.  
> Предлагаем policy: удалять только `* ([0-9]*).*` старше 14d после вашего GO (оригиналы без `(N)` не трогаем).  
> Нужен ACK / запрет.
