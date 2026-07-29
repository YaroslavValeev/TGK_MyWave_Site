# Owner — D+E: staging + parser downloads

**Дата:** 2026-07-29  
**D:** `mywave-staging` inspect → optional stop (tree не удалять)  
**E:** `/opt/bot3/parser-new-bot/downloads` diagnose only (без `rm`)  
**Не трогать:** `mywave-site` · `mywave-node` · `mywave-telegram-bot` · live parser WD · docker volumes  

---

## D1 — Staging inspect

```bash
systemctl is-active mywave-staging
systemctl is-enabled mywave-staging
systemctl cat mywave-staging.service | sed -n '1,50p'

sudo du -sh /var/www/mywave-staging 2>/dev/null || echo 'no staging tree'
ss -lntp | grep -E ':5002|:5000|:5001' || true
curl -fsS -m 5 http://127.0.0.1:5002/health 2>&1 || echo 'staging_health_fail'

sudo journalctl -u mywave-staging -n 30 --no-pager -o short-iso
sudo grep -RInE '5002|staging\.mywave|mywave-staging' /etc/nginx 2>/dev/null | head -20 || echo 'no_nginx_hits'
```

**STOP-OK если:** нет плана E2E на неделе · в journal тишина · nginx без upstream на `:5002`.

---

## D2 — Optional stop (только после STOP-OK)

```bash
sudo systemctl stop mywave-staging
# автозапуск после reboot выключить (по желанию):
# sudo systemctl disable mywave-staging

systemctl is-active mywave-staging || true
ss -lntp | grep 5002 || echo '5002_closed'
curl -fsS https://mywavewake.ru/health | python3 -c 'import sys,json; print(json.load(sys.stdin).get("status"))'
systemctl is-active mywave-site mywave-telegram-bot mywave-node
```

**Rollback:**
```bash
sudo systemctl start mywave-staging
# sudo systemctl enable mywave-staging
systemctl is-active mywave-staging
curl -fsS -m 5 http://127.0.0.1:5002/health || true
```

**Не делать:** `rm -rf /var/www/mywave-staging` в этой волне.

---

## E1 — Parser downloads (только чтение)

```bash
PARSER_WD=/opt/bot3/parser-new-bot
DL=$PARSER_WD/downloads

systemctl is-active parser-news-bot
systemctl cat parser-news-bot.service | grep -E 'WorkingDirectory|ExecStart'

df -h /
sudo du -sh /opt/bot3 "$PARSER_WD" "$DL" 2>/dev/null
sudo ls -lah /opt/bot3

echo '=== downloads depth1 ==='
sudo du -xh "$DL" --max-depth=1 2>/dev/null | sort -h | tail -20

echo '=== age buckets ==='
for d in 7 14 30 90; do
  n=$(sudo find "$DL" -xdev -type f -mtime +$d 2>/dev/null | wc -l)
  echo "files_mtime_gt_${d}d=$n"
done

echo '=== largest 20 ==='
sudo find "$DL" -xdev -type f -printf '%s\t%TY-%Tm-%Td\t%p\n' 2>/dev/null | sort -n | tail -20

echo '=== tmp/cache candidates (list) ==='
sudo find "$PARSER_WD" -xdev -maxdepth 3 \( -iname '*tmp*' -o -iname '*.tmp' -o -iname '*cache*' \) 2>/dev/null | head -50
sudo test -d "$DL/tmp" && sudo du -sh "$DL/tmp" && sudo find "$DL/tmp" -type f -mtime +14 | head -30 || echo 'no downloads/tmp'
```

**Не удалять** `downloads` / `review_media` без GO Parser-команды.

---

## PASS

| Блок | PASS |
|------|------|
| D1 | status/size/port/nginx/journal получены |
| D2 | staging inactive · prod health ok · site/bot/node active |
| E1 | размеры + age + largest без `rm` |

Пришлите вывод D1 + E1 → решим stop staging и есть ли safe tmp-цели.  
