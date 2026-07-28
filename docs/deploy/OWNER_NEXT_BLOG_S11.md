# Owner — следующий этап после YClients (Blog → S11)

**Дата:** 2026-07-29  
**YClients S5–S10:** CLOSED на prod  
**Camp:** hold (Tour отладка; cron OFF; public может быть ON с пустой витриной)

---

## Быстрый health (Site + Bot)

```bash
systemctl is-active mywave-site mywave-telegram-bot
cd /var/www/mywave && git branch --show-current && git log -1 --oneline
cd /opt/mywave-bot && git branch --show-current && git log -1 --oneline
curl -fsS https://mywavewake.ru/health
curl -sS "https://mywavewake.ru/api/calendar/slots/$(date -d '+3 days' +%F)?service=boat" | python3 -m json.tool | head -20
```

---

## Blog diagnose — PASS (Owner 2026-07-29)

Проверено на prod:

| Check | Result |
|-------|--------|
| Site SHA | diagnose на `07a3369f`; SEO — следующий commit на main |
| `/blog` | **200** |
| `/api/blog/latest` | JSON OK |
| `/api/blog/posts?limit=5` | JSON OK, items есть |

**Качество контента (editorial, не 500):** кириллические/длинные slug, emoji в title, пустые tags, fallback `Place1Logo.png`, `video_url: null`. Это B1/checklist + ParserNews, не блокер витрины.

---

## B2 backlog — статус кода

| Пункт backlog | Статус |
|---------------|--------|
| Latest / preview на главной | **DONE** (`blog_preview_posts` в `index.html`) |
| Поиск `?q=` + пагинация | **DONE** (`templates/blog/index.html` + `blog.py`) |
| Категории (legacy) | **нет UI** — только теги `#tag` |
| SEO list/post canonical+OG | **в main** (этот commit; нужен pull+restart) |

---

## Деплой SEO-патча (после push в main)

**Проект:** Site MyWave  
**Сервер:** `4169037-ep26382`  
**cwd:** `/var/www/mywave`  
**Сервисы:** только `mywave-site`  
**Не трогать:** `mywave-node`, bot, Camp cron

```bash
cd /var/www/mywave
git fetch origin
git log -1 --oneline
git pull --ff-only origin main
git log -1 --oneline
# ожидаемо: новый SHA с SEO blog templates

sudo systemctl restart mywave-site
systemctl is-active mywave-site
# ожидаемо: active
```

**Rollback:**

```bash
cd /var/www/mywave
git checkout <SHA_ДО_SEO>
sudo systemctl restart mywave-site
```

---

## Проверка после SEO-деплоя

```bash
# list: canonical + og
curl -sS https://mywavewake.ru/blog | grep -E 'rel="canonical"|og:title|og:url' | head -10

# поиск
curl -sS -o /dev/null -w "%{http_code}\n" "https://mywavewake.ru/blog?q=foil"
curl -sS "https://mywavewake.ru/blog?q=foil" | grep -E 'Поиск:|blog-card-title|Пока нет' | head -15

# post: canonical не request.url с мусором
SLUG=$(curl -sS https://mywavewake.ru/api/blog/latest | python3 -c 'import sys,json; print(json.load(sys.stdin)["slug"])')
curl -sS "https://mywavewake.ru/blog/$SLUG" | grep -E 'rel="canonical"|og:url' | head -5

# главная: блок блога
curl -sS https://mywavewake.ru/ | grep -E 'blog-section|blog-home-card|Все публикации' | head -10
```

**PASS:** `/blog` отдаёт `<link rel="canonical" …/blog>`, поиск 200, главная с карточками.

---

## Blog — волны дальше

| # | Scope | Док |
|---|-------|-----|
| B1 | Editorial checklist + ParserNews contract (процесс) | `docs/BLOG_EDITORIAL_CHECKLIST.md`, `docs/BLOG_CONTRACT_v1.md` |
| B2 | Backlog UX/SEO | DONE после pull SEO commit |
| B3 | Video + CSP | `docs/architecture/BLOG_RUNTIME_CANON.md` |
| B4 | Admin Blog write workflow | Site Admin |
| S11 | Final Site audit | после B1–B4 |

---

## Не делать без GO

- Camp import/cron
- `YCLIENTS_WRITE_ENABLED=0` rollback без причины
- Push force на main
- Restart `mywave-node`

---

## Опциональный мелкий техдолг YClients (не блокер)

После gateway reschedule бот иногда логирует `Invalid sequence value` на GCal — SoT уже обновлён mirror’ом; двойной update в боте можно убрать отдельным мелким PR.
