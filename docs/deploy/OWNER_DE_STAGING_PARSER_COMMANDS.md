# Owner — D+E результат (2026-07-29)

## D — staging: KEEP

| Факт | Значение |
|------|----------|
| Unit | `active` + `enabled` |
| Path | `/var/www/mywave-staging` (~1.9G) |
| Bind | `127.0.0.1:5002` |
| Nginx | `staging.mywavewake.ru` → `:5002` (**sites-enabled**) |

**Решение:** **не stop / не disable** — публичный staging URL живой. Stop → 502 на subdomain, RAM↑ мало, диск **не** освободится (дерево останется).

Удаление `/var/www/mywave-staging` — только отдельный GO + отключение nginx vhost.

## E — parser downloads: diagnose DONE, purge HOLD

| Факт | Значение |
|------|----------|
| WD | `/opt/bot3/parser-new-bot` (live) |
| bot3 total | ~4.7G |
| `downloads/tmp` | нет |
| files mtime>7d | 2880 |
| files mtime>14d/30d | 1153 |
| files mtime>90d | 302 |
| Крупные | дубли `IMG_*.MOV/(N)` и `IMG_9147*.mp4` ~40–90MB |

**Решение:** **не `rm`**. Кандидат на будущее (Parser GO): дубликаты имени `file (N).ext`.

---

## Команды — добор (сейчас)

```bash
# D — добить health/ports/journal
ss -lntp | grep -E ':5002|:5000|:5001' || true
curl -fsS -m 5 http://127.0.0.1:5002/health || echo 'staging_health_fail'
curl -fsS -m 5 -o /dev/null -w "staging_dns %{http_code}\n" https://staging.mywavewake.ru/health || echo 'staging_public_fail'
sudo journalctl -u mywave-staging -n 30 --no-pager -o short-iso

systemctl is-active mywave-site mywave-staging mywave-telegram-bot mywave-node parser-news-bot
```

```bash
# E — размеры + оценка дублей (БЕЗ удаления)
PARSER_WD=/opt/bot3/parser-new-bot
DL=$PARSER_WD/downloads

sudo du -sh "$DL" "$PARSER_WD" /opt/bot3
sudo du -xh "$DL" --max-depth=1 2>/dev/null | sort -h | tail -20

# сколько места в именах " (N)." — только подсчёт
sudo find "$DL" -xdev -type f -name '* ([0-9]*).*' -printf '%s\n' 2>/dev/null \
  | awk '{s+=$1; n++} END {printf "dup_like_files=%d bytes=%d ~%.2fG\n", n+0, s+0, s/1024/1024/1024}'

# список 30 крупнейших дубль-подобных (для Parser)
sudo find "$DL" -xdev -type f -name '* ([0-9]*).*' -printf '%s\t%TY-%Tm-%Td\t%p\n' 2>/dev/null \
  | sort -n | tail -30
```

## Опционально позже (GO)

```bash
# D — stop staging (сломает staging.mywavewake.ru):
# sudo systemctl stop mywave-staging && sudo systemctl disable mywave-staging

# E — удаление дублей ТОЛЬКО после ACK Parser:
# НЕ запускать без списка и бэкапа
```
