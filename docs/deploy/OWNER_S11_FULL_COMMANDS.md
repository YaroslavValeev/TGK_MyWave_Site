# Owner — S11 full (после B4.2, без Camp)

**Prod SHA:** `9b8e22f1`  
**Сервисы:** только читать/restart `mywave-site` при необходимости; **не** трогать `mywave-node`  
**Camp:** HOLD  

**Уже PASS:** S11-light · B4.2 admin save (`final_posts`+video в flash)

---

## 0) Public post (Foiling Week) — после B4.2 save

В браузере (админка, уже залогинены):

1. Карточка поста → **Сбросить кэш**  
2. **Открыть на сайте**  

На сервере (slug из карточки):

```bash
SLUG='foiling-week-2026-was-a-big-success-for-all-compet-1ff8a7'
curl -sS -o /dev/null -w "post %{http_code}\n" "https://mywavewake.ru/blog/${SLUG}"
# фрагмент из вашей правки final_posts (подставьте свой текст):
curl -fsS "https://mywavewake.ru/blog/${SLUG}" | grep -F 'Foiling Week' | head -3
```

**PASS:** post `200` + текст правки виден в HTML.

---

## 1) Runtime A

```bash
cd /var/www/mywave
git log -1 --oneline
# ожидаемо: 9b8e22f1 …

systemctl is-active mywave-site mywave-telegram-bot
# оба: active
# mywave-node: НЕ restart

curl -fsS https://mywavewake.ru/health | python3 -c 'import sys,json; print(json.load(sys.stdin).get("status"))'
# ok
```

---

## 2) Boat B (JSON, не только HTTP)

```bash
curl -fsS "https://mywavewake.ru/api/calendar/slots/$(date -d '+3 days' +%F)?service=boat" \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print(type(d).__name__, len(d) if hasattr(d,"__len__") else d)'
```

Опционально (Telegram): одна тестовая бронь create → reschedule → cancel.

---

## 3) Blog public C

```bash
curl -fsS https://mywavewake.ru/blog | grep -c 'property="og:title"'
# ожидаемо: 1

curl -fsS https://mywavewake.ru/blog | grep -i 'rel="canonical"' | head -2

curl -sS -o /dev/null -w "q %{http_code}\n" "https://mywavewake.ru/blog?q=foil"
# q 200

curl -sS https://mywavewake.ru/api/blog/latest | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("slug"), (d.get("title") or "")[:60])'

curl -sS -o /dev/null -w "home %{http_code}\n" https://mywavewake.ru/
# home 200
```

Браузер: главная `#blog` — карточки видны.  
CSP (view-source / DevTools): `frame-src` с youtube/vk/rutube; `media-src` допускает `https:`.

---

## 4) Admin D (состояние write)

```bash
grep -E '^BLOG_ADMIN_WRITE_ENABLED=' /var/www/mywave/.env || true
```

- Сейчас после B4.2 обычно `=1` — ок, пока идёт редактура.  
- После работы вернуть default OFF (по политике checklist):

```bash
# только если решили выключить write:
# sudo sed -i 's/^BLOG_ADMIN_WRITE_ENABLED=.*/BLOG_ADMIN_WRITE_ENABLED=0/' /var/www/mywave/.env
# sudo systemctl restart mywave-site
# systemctl is-active mywave-site
```

---

## 5) Camp E — только HOLD-check

```bash
grep -E 'mywave-camp|^#0' /etc/cron.d/mywave-camp-sync 2>/dev/null | head -5
# ожидаемо: строка с #0 … camp-sync (закомментирована)
```

**Не** uncomment / enable без явного GO.

---

## PASS / FAIL

| Блок | PASS если |
|------|-----------|
| 0 | публичный пост отражает save |
| 1 | SHA tip · site+bot active · health ok |
| 2 | boat JSON не пустой / валидный |
| 3 | og:title=1 · q/home 200 · latest отвечает |
| 5 | camp cron commented |

Пришлите вывод блоков **0–3 и 5** — отметим S11 full CLOSED (без Camp).

---

## Не делать без GO

- Camp sync / cron enable  
- restart `mywave-node`  
- массовый rewrite всех постов  
- YClients write-path changes  
