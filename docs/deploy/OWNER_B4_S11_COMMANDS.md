# Owner — B4 Admin Blog MVP + S11 audit smoke

**Проект:** Site MyWave  
**Сервер:** `4169037-ep26382`  
**cwd:** `/var/www/mywave`  
**Сервис:** только `mywave-site`  
**Не трогать:** `mywave-node`, bot, Camp cron, YClients write

**Предыдущие CLOSED:** YClients S5–S10 · Blog B2 · Blog B1/B3 (`d1fe85ed`)

**Этот релиз:** B4-MVP — `/admin/blog/<slug>` деталка + writeback SEO/карточки в `raw_feed` (флаг OFF по умолчанию) + S11 checklist.

---

## 1) Pull + restart

```bash
cd /var/www/mywave
git fetch origin
git log -1 --oneline
git pull --ff-only origin main
git log -1 --oneline
# ожидаемо: новый SHA (B4 admin blog)

sudo systemctl restart mywave-site
systemctl is-active mywave-site
# ожидаемо: active
```

**Rollback:**

```bash
cd /var/www/mywave
git checkout d1fe85ed
sudo systemctl restart mywave-site
```

---

## 2) Smoke публичного блога (регрессия)

```bash
curl -sS -o /dev/null -w "%{http_code}\n" https://mywavewake.ru/blog
curl -sS -o /dev/null -w "%{http_code}\n" https://mywavewake.ru/blog?q=foil
curl -sS https://mywavewake.ru/api/blog/latest | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("slug"), d.get("title","")[:60])'
curl -fsS https://mywavewake.ru/health | python3 -c 'import sys,json; print(json.load(sys.stdin).get("status"))'
```

**PASS:** `200` / `200` / slug+title / `ok`

---

## 3) Admin read (без write)

В браузере (залогиненным admin):

1. `https://mywavewake.ru/admin/blog` — список + кнопка «Карточка»
2. Открыть карточку — поля видны, запись **OFF**
3. «Сбросить кэш блога» — flash success

CLI (ожидаемо redirect на login, не 500):

```bash
curl -sS -o /dev/null -w "%{http_code}\n" https://mywavewake.ru/admin/blog
# ожидаемо: 302 (login) или 200 если сессия
```

---

## 4) Включить write (Owner GO) — опционально

Только после smoke §2–3:

```bash
cd /var/www/mywave
# бэкап .env
cp -a .env .env.bak.b4-$(date +%Y%m%d%H%M)

# добавить/обновить флаг (если строки нет — append)
grep -q '^BLOG_ADMIN_WRITE_ENABLED=' .env \
  && sed -i 's/^BLOG_ADMIN_WRITE_ENABLED=.*/BLOG_ADMIN_WRITE_ENABLED=1/' .env \
  || echo 'BLOG_ADMIN_WRITE_ENABLED=1' >> .env

grep '^BLOG_ADMIN_WRITE_ENABLED=' .env
sudo systemctl restart mywave-site
systemctl is-active mywave-site
```

Проверка в UI `/admin/settings`: флаг `BLOG_ADMIN_WRITE_ENABLED` = true.

На карточке поста: правка **тегов** или **excerpt** → «Сохранить в raw_feed» → flash с перечнем колонок → обновить `/blog/<slug>`.

**Откат флага:**

```bash
sed -i 's/^BLOG_ADMIN_WRITE_ENABLED=.*/BLOG_ADMIN_WRITE_ENABLED=0/' /var/www/mywave/.env
sudo systemctl restart mywave-site
```

---

## 5) S11 smoke checklist (site)

```bash
echo "=== SERVICES ==="
systemctl is-active mywave-site mywave-telegram-bot

echo "=== SHA ==="
cd /var/www/mywave && git log -1 --oneline
cd /opt/mywave-bot && git log -1 --oneline

echo "=== HEALTH / BOAT / BLOG ==="
curl -fsS https://mywavewake.ru/health
curl -sS -o /dev/null -w "boat_slots %{http_code}\n" "https://mywavewake.ru/api/calendar/slots/$(date -d '+3 days' +%F)?service=boat"
curl -sS -o /dev/null -w "blog %{http_code}\n" https://mywavewake.ru/blog
curl -sS -o /dev/null -w "home %{http_code}\n" https://mywavewake.ru/

echo "=== CAMP HOLD ==="
grep -E '^CAMP_|mywave-camp' /var/www/mywave/.env /etc/cron.d/mywave-camp-sync 2>/dev/null | head -20
```

**PASS S11-light:** site+bot active · health ok · boat slots 200 · blog/home 200 · camp cron всё ещё commented / без GO.

Полный S11 (SEO/security/ops) — отдельный аудит после стабилизации B4 write на 1–2 постах.

---

## Не делать без GO

- `BLOG_ADMIN_WRITE_ENABLED=1` без бэкапа `.env`
- правка `final_posts` через админку (её нет — так и задумано)
- Camp cron enable
- YClients write off
- restart `mywave-node`
