# Owner — YClients hotfix: slot 30 + amount=N

**SHA:** после push (seance N×30 + services.amount=N)  
**Контекст:** партнёр — 1 сет закрывает 30 мин (25+5); 3 сета → 90 мин + 3× услуга 25 мин  
**Сервис:** только `mywave-site`

**Уже CLOSED:** S5–S10; баг: create писал N×25 и amount отсутствовал → 75 мин / qty=1.

---

## Deploy

```bash
cd /var/www/mywave
git pull --ff-only origin main
git log -1 --oneline
# ожидаемо: … yclients seance slot 30 + service amount

sudo systemctl restart mywave-site
systemctl is-active mywave-site
curl -fsS https://mywavewake.ru/health | python3 -c 'import sys,json; print(json.load(sys.stdin).get("status"))'
curl -fsS "https://mywavewake.ru/api/calendar/slots/$(date -d '+3 days' +%F)?service=boat" \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print(type(d).__name__, len(d) if hasattr(d,"__len__") else d)'
```

**Rollback:**
```bash
cd /var/www/mywave
git checkout HEAD~1   # или предыдущий known-good SHA
sudo systemctl restart mywave-site
```

---

## Verify (новая тестовая бронь)

1. Сайт: 1 сет → в YC длительность **30 мин**, кол-во услуги **1**  
2. Сайт: 3 сета → в YC **90 мин** (не 75), кол-во **3**  
3. `mw_source` / `mw_id` без изменений  

Старую запись `bk_1683308630c5` / 01.08 15:00–16:15 код **не чинит** — поправьте вручную в YC: end +15 мин (→16:30) и кол-во 3.

---

## Не делать

- менять `BOAT_SEANCE_MINUTES` на 30 в `.env` вместо деплоя фикса  
- restart `mywave-node`  
