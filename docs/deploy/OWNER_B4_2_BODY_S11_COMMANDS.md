# Owner — B4.2 body/video edit + S11 light

**SHA ожидаемый:** commit B4.2 (final_posts + video URLs в админке)  
**Сервис:** только `mywave-site`  
**Флаг:** `BLOG_ADMIN_WRITE_ENABLED=1`

**Уже CLOSED:** YClients · Blog diagnose · B2 · B1/B3 · B4.1 autofill · B4.1b SEO checklist (`397e663a`)

---

## 1) Deploy

```bash
cd /var/www/mywave
git pull --ff-only origin main
git log -1 --oneline
# ожидаемо: … B4.2 admin body/video

sudo systemctl restart mywave-site
systemctl is-active mywave-site
```

**Rollback:**
```bash
cd /var/www/mywave
git checkout 397e663a
sudo systemctl restart mywave-site
```

---

## 2) Smoke

```bash
systemctl is-active mywave-site mywave-telegram-bot
curl -fsS https://mywavewake.ru/health | python3 -c 'import sys,json; print(json.load(sys.stdin).get("status"))'
curl -sS -o /dev/null -w "blog %{http_code}\n" https://mywavewake.ru/blog
curl -sS -o /dev/null -w "boat %{http_code}\n" "https://mywavewake.ru/api/calendar/slots/$(date -d '+3 days' +%F)?service=boat"
grep -E 'mywave-camp|^#0' /etc/cron.d/mywave-camp-sync 2>/dev/null | head -5
```

**PASS S11-light:** site+bot active · health ok · blog/boat 200 · camp cron HOLD.

---

## 3) UI B4.2

1. `/admin/blog` → Карточка  
2. Есть textarea **Текст статьи (final_posts)** + поля video_url / embed_url / постер  
3. Малое изменение текста → без чекбокса «Подтверждаю запись final_posts» save **блокируется**  
4. С чекбоксом → save → flash со `final_posts` в списке колонок  
5. «Открыть на сайте» — текст виден после сброса кэша  

**Осторожно:** запись `final_posts` перезаписывает поле Parser в Sheets.

---

## Не делать без GO

- Camp sync / cron enable  
- YClients write off  
- restart `mywave-node`  
- Массовый rewrite всех постов
