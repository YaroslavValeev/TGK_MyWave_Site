# Owner — deploy YC human comment labels

**SHA target:** `68ea9666` · **deployed prod 2026-07-31** · site active · health ok  
**Host:** `4169037-ep26382` · `/var/www/mywave`  
**Сервис:** только `mywave-site` · **не** трогать `mywave-node`

**Status:** CLOSED PASS (pull + restart)

Новый comment: `через сайт | mw_id=…` · `через ТГ | mw_id=…`  
Старые записи в YC **не** обновляются автоматически.

---

## Deploy

```bash
cd /var/www/mywave
git fetch origin main
git log -1 --oneline
git pull --ff-only origin main
git log -1 --oneline
```

```bash
sudo systemctl restart mywave-site
systemctl is-active mywave-site
```

```bash
curl -fsS https://mywavewake.ru/health | python3 -c 'import sys,json; print(json.load(sys.stdin).get("status"))'
```

**PASS:** HEAD содержит yclients human comment · site `active` · health `ok`.

---

## Verify (новая тестовая бронь)

1. Сайт → создать/smoke бронь → в YC comment: **`через сайт | mw_id=…`** (не `mw_source=site`)  
2. Если есть ТГ-бот запись → **`через ТГ | mw_id=…`**  
3. Старую 01.08 при желании поправьте вручную в YC

---

## Rollback

```bash
cd /var/www/mywave
git checkout HEAD~1
sudo systemctl restart mywave-site
```

(или известный good SHA)

## Не делать

- restart `mywave-node`
- mass-edit старых записей через API без GO
