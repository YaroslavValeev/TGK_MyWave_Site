# Owner — Parser downloads cleanup (logical order)

**Auth:** Owner GO 2026-07-29 (Site ops; originals без `(N)` не трогаем)  
**WD:** `/opt/bot3/parser-new-bot/downloads`  
**Ожидание:** ~2398 дублей ≈ 3.3G · downloads 4.3G → ~1G после  

Порядок: **0 preflight → 1 dry-run → 2 delete → 3 verify**.  
Paste **по одной команде** (или целый блок как есть). Между шагами 1 и 2 не обязателен ответ — если числа близки к ожиданию, сразу шаг 2.

---

## 0) Preflight

```bash
systemctl is-active parser-news-bot mywave-site
```

```bash
df -h /
```

```bash
sudo du -sh /opt/bot3/parser-new-bot/downloads
```

```bash
ls -ld /opt/bot3/parser-new-bot/downloads /opt/bot3/parser-new-bot/review_media 2>/dev/null || true
```

**PASS:** parser+site `active` · downloads обычная папка · `review_media` отдельно.

---

## 1) Dry-run

```bash
DL=/opt/bot3/parser-new-bot/downloads
echo "=== ZERO ==="; sudo find "$DL" -xdev -type f -size 0 | wc -l
echo "=== DUP all ==="; sudo find "$DL" -xdev -type f -name '* ([0-9]*).*' ! -size 0 -printf '%s\n' | awk '{s+=$1;n++} END{printf "n=%d ~%.2fG\n", n+0, s/1024/1024/1024}'
echo "=== DUP +14d ==="; sudo find "$DL" -xdev -type f -name '* ([0-9]*).*' ! -size 0 -mtime +14 -printf '%s\n' | awk '{s+=$1;n++} END{printf "n=%d ~%.2fG\n", n+0, s/1024/1024/1024}'
```

**Gate → шаг 2:** `DUP all` примерно `n=2000–3000` и `~2.5–4.0G`.  
Если `n=0` или `>10000` / размер не похож — **стоп**, пришлите вывод.

---

## 2) Delete (full: zero + все дубли (N))

Один блок (после PASS gate шага 1):

```bash
DL=/opt/bot3/parser-new-bot/downloads
LOG=/root/parser_dl_cleanup_$(date +%Y%m%d_%H%M%S)
echo "ZERO delete:"; sudo find "$DL" -xdev -type f -size 0 -print -delete | tee "${LOG}.zero" | wc -l
echo "DUP delete:"; sudo find "$DL" -xdev -type f -name '* ([0-9]*).*' ! -size 0 -print -delete | tee "${LOG}.dups" | wc -l
echo "logs: ${LOG}.zero ${LOG}.dups"
```

---

## 3) Verify

```bash
sudo du -sh /opt/bot3/parser-new-bot/downloads
```

```bash
df -h /
```

```bash
systemctl is-active parser-news-bot mywave-site mywave-telegram-bot mywave-node
```

```bash
curl -fsS https://mywavewake.ru/health | python3 -c 'import sys,json; print(json.load(sys.stdin).get("status"))'
```

```bash
curl -o /dev/null -s -w '%{http_code}\n' https://mywavewake.ru/blog/
```

**PASS:** downloads ≪ 4.3G (цель ~0.8–1.5G) · сервисы active · health ok · blog 200.

---

## 4) Следующая волна (после PASS шага 3)

1. Сообщение Parser: «дубли ` (N)` сняты; поправьте сохранение — не минтить `(1)`, `(2)`»  
2. Nginx orphan staging vhost (DNS NXDOMAIN) — опционально  
3. Camp: 1 pending в admin moderate  
4. YC: текст партнёру по старому бронированию 01.08 (если ещё нужно)

---

## Не делать

- `rm -rf downloads` / трогать код Parser  
- `docker volume prune`  
- restart `mywave-node` без нужды  
- удалять имена **без** ` (N)`
