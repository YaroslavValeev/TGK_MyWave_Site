# Owner — next ops after E purge (nginx staging orphan → camp)

**Pref:** E downloads purge CLOSED · disk 64% · downloads 920M  
**Порядок:** blog API recheck → nginx staging vhost diagnose → (optional disable) → camp pending

---

## A) Blog API (исправленная одна строка)

```bash
curl -fsS 'https://mywavewake.ru/api/blog/posts?limit=5' | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("total"), len(d.get("items") or []))'
```

**PASS:** два числа (total и len items), без SyntaxError.  
`/blog/` → 404 нормально (только `/blog/<slug>`).

---

## B) Nginx staging orphan — diagnose

```bash
sudo nginx -T 2>/dev/null | grep -nE 'staging\.mywavewake|listen 5002|proxy_pass.*5002' || true
```

```bash
ls -la /etc/nginx/sites-enabled/ /etc/nginx/sites-available/ 2>/dev/null | grep -iE 'stag|mywave' || true
```

```bash
getent hosts staging.mywavewake.ru || echo 'DNS NXDOMAIN-or-missing'
```

Пришлите вывод. Если есть enable-линк на staging vhost → блок C.

---

## C) Nginx staging — disable vhost (GO после B 2026-07-29)

**Факт B:** `sites-enabled/staging.mywavewake.ru` → `sites-available/...`; proxy `:5002`; DNS NXDOMAIN.

```bash
sudo rm -f /etc/nginx/sites-enabled/staging.mywavewake.ru
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

```bash
sudo nginx -T 2>/dev/null | grep -nE 'staging\.mywavewake|proxy_pass.*5002' || echo 'staging vhost gone from active config'
```

```bash
ls -la /etc/nginx/sites-enabled/ | grep -iE 'stag|mywave' || true
```

```bash
curl -fsS https://mywavewake.ru/health | python3 -c 'import sys,json; print(json.load(sys.stdin).get("status"))'
```

```bash
systemctl is-active mywave-site nginx
```

**Не удалять:** `sites-available/staging.mywavewake.ru`, дерево `/var/www/mywave-staging`, unit.  
**Rollback:**  
`sudo ln -s /etc/nginx/sites-available/staging.mywavewake.ru /etc/nginx/sites-enabled/staging.mywavewake.ru && sudo nginx -t && sudo systemctl reload nginx`

---

## D) Camp — pending (после C PASS 2026-07-29)

```bash
curl -fsS https://mywavewake.ru/health | python3 -c 'import sys,json; print(json.load(sys.stdin).get("status"))'
```

```bash
curl -sS -o /dev/null -w 'camps %{http_code}\n' https://mywavewake.ru/camps
```

```bash
curl -sS -o /dev/null -w 'admin_camp %{http_code}\n' https://mywavewake.ru/admin/camp/
```

Сводка статусов (prod):

```bash
cd /var/www/mywave && sudo -u www-data FLASK_CONFIG=production /var/www/mywave/venv/bin/python -c "from app import create_app; from app.database.camp_models import Camp; from app.database.models import db; from collections import Counter; app=create_app();
ctx=app.app_context(); ctx.push(); print(dict(Counter(s for (s,) in db.session.query(Camp.publication_status).all())))"
```

**UI:** https://mywavewake.ru/admin/camp/?status=pending_review  
Для каждого pending: открыть → Publish или Hide (не mass-publish).

```bash
curl -sS -o /dev/null -w 'camps_after %{http_code}\n' https://mywavewake.ru/camps
```


---

## Не делать

- `rm -rf /var/www/mywave-staging`
- enable staging обратно без DNS
- restart `mywave-node`
