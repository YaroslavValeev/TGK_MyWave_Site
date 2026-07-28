# Owner — Blog B1/B3 deploy + verify (после YClients CLOSED)

**Дата:** 2026-07-29  
**Prod cwd:** `/var/www/mywave`  
**Сервис:** только `mywave-site`  
**Не трогать:** `mywave-node`, bot, Camp cron, YClients write

**Уже CLOSED на prod:** YClients S5–S10 · Blog diagnose · B2 SEO (`c70b13f6`)

**Этот релиз:** B1 display/slug hygiene + dual og:title fix + B3 CSP video hosts/media-src + editorial checklist

---

## 1) Pull + restart

```bash
cd /var/www/mywave
git fetch origin
git log -1 --oneline
git pull --ff-only origin main
git log -1 --oneline
# ожидаемо: новый SHA (B1/B3), не c70b13f6

sudo systemctl restart mywave-site
systemctl is-active mywave-site
# ожидаемо: active
```

**Rollback:**

```bash
cd /var/www/mywave
git checkout c70b13f6
sudo systemctl restart mywave-site
systemctl is-active mywave-site
```

---

## 2) Verify SEO (один og:title) + search + home

```bash
echo "=== SEO /blog ==="
curl -sS -o /tmp/blog.html -w "HTTP %{http_code}\n" https://mywavewake.ru/blog
grep -c 'property="og:title"' /tmp/blog.html
grep -E 'rel="canonical"|property="og:title"|property="og:url"' /tmp/blog.html | head -10
# PASS: HTTP 200; count og:title == 1; canonical + blog og:title

echo "=== SEARCH ==="
curl -sS -o /dev/null -w "%{http_code}\n" "https://mywavewake.ru/blog?q=foil"
# PASS: 200

echo "=== HOME ==="
curl -sS https://mywavewake.ru/ | grep -E 'id="blog"|blog-home-card|Все публикации' | head -8
# PASS: section + cards
```

---

## 3) Verify title hygiene (API) + CSP video

```bash
echo "=== LATEST TITLE ==="
curl -sS https://mywavewake.ru/api/blog/latest | python3 -m json.tool | head -25
# PASS: title без ведущего emoji (если был); slug может остаться кириллическим у СТАРЫХ строк из Sheets

echo "=== CSP frame/media ==="
curl -sSI https://mywavewake.ru/blog | tr -d '\r' | grep -i content-security-policy | head -1
# PASS: в CSP есть youtube + rutube/vk (или kinescope) и media-src допускает https:
```

---

## 4) Что остаётся Owner/Parser (не код сайта)

В Sheets (`raw_feed`) для **новых** строк перед `READY_TO_PUBLISH`:

- короткий **ASCII slug**
- обложка (не Place1Logo)
- 1–4 тега
- video_url/embed при наличии видео

Чеклист: `docs/BLOG_EDITORIAL_CHECKLIST.md`

---

## 5) Дальше по дорожной карте

| Волна | Статус |
|-------|--------|
| B1 editorial+hygiene | этот релиз (код) + процесс в Sheets |
| B2 UX/SEO | CLOSED |
| B3 video CSP | этот релиз (allowlist) |
| B4 Admin write | следующий код-эпик (нужен GO) |
| S11 Final audit | после B4 или по GO |
| Camp | HOLD |

---

## Не делать без GO

- Camp import/cron enable
- YClients write off
- Restart `mywave-node`
- Массовый rewrite уже опубликованных slug в Sheets (ломает URL)
