# Owner — remaining ops (Site) after YC human comment

**Prod HEAD:** `2eda1f13` · health ok · human labels True  
**Verify A–E 2026-07-31 01:09:** **CLOSED PASS**  
- downloads **924M** · `(N)` sized dups **0**  
- staging tree **1.9G** kept · unit inactive/disabled  
- camp `{archived:3, published:1}`  

**Не трогать:** `mywave-node` · Tour autopublish (команда Tour)  
**CLOSED:** Parser no-`(N)` code fix 2026-07-31 (prod patched · VERIFY_OK)  
**OPEN вне Site:** YC 01.08 UI · Tour autopublish · optional `rm` staging tree


---

## 1) Verify human comment deploy (read-only)

```bash
cd /var/www/mywave
git log -1 --oneline
systemctl is-active mywave-site
curl -fsS https://mywavewake.ru/health | python3 -c 'import sys,json; print(json.load(sys.stdin).get("status"))'
```

```bash
python3 - <<'PY'
import pathlib
p = pathlib.Path('/var/www/mywave/app/services/booking/providers/yclients.py')
t = p.read_text(encoding='utf-8')
print('has_human_labels', 'через сайт' in t and 'SOURCE_HUMAN_LABELS' in t)
PY
```

**PASS:** `68ea9666` · active · ok · `has_human_labels True`

---

## 2) Optional — размер staging tree (не удалять без второго GO)

```bash
sudo du -sh /var/www/mywave-staging 2>/dev/null || echo 'no staging tree'
```

```bash
systemctl is-active mywave-staging; systemctl is-enabled mywave-staging
```

```bash
ls /etc/nginx/sites-enabled/ | grep -i stag || echo 'staging vhost not enabled (ok)'
```

Если решите удалить дерево позже (отдельный ACK):  
`# sudo rm -rf /var/www/mywave-staging` — **не сейчас**

---

## 3) YC старая бронь 01.08 — только UI партнёра

В приложении YClients найти запись **01.08 15:00–16:15** с  
`mw_id=bk_1683308630c5` / катер Axis:

1. Конец → **16:30**  
2. Кол-во услуги 25 мин → **3**  
3. Comment (опционально): `через сайт | mw_id=bk_1683308630c5`

На сервере Site **ничего не запускать** для этой правки.

---

## 4) Parser downloads — контроль, что дубли не растут

```bash
sudo du -sh /opt/bot3/parser-new-bot/downloads
```

```bash
sudo find /opt/bot3/parser-new-bot/downloads -xdev -type f -name '* ([0-9]*).*' ! -size 0 | wc -l
```

**Ожидание:** размер ~≤1G · число `(N)` мало/0. Если снова тысячи — Parser ещё минтит дубли.

---

## 5) Camp sanity (production create_app)

```bash
cd /var/www/mywave && sudo -u www-data env FLASK_CONFIG=production ./venv/bin/python -c "from collections import Counter; from app import create_app; from app.database.camp_models import Camp; from app.database.models import db; app=create_app('production');
ctx=app.app_context(); ctx.push(); print(dict(Counter(s for (s,) in db.session.query(Camp.publication_status).all())))"
```

**PASS:** `published` ≥ 1 · без traceback.

---

## Не делать

- `flask migrate-blog` на prod (CLI sqlite-oriented; prod schema иначе)  
- restart `mywave-node`  
- `rm -rf downloads` / `rm -rf mywave-staging` без явного GO  
- Tour autopublish enable без команды Tour
