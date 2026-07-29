# Owner — B4.1 Admin Blog UX (autofill SEO/tags)

**SHA ожидаемый:** после `git pull` — commit `feat(blog): admin card autofill SEO/tags`  
**Сервис:** только `mywave-site`  
**Флаг:** `BLOG_ADMIN_WRITE_ENABLED=1` (уже включён)

---

## 1) Deploy

```bash
cd /var/www/mywave
git pull --ff-only origin main
git log -1 --oneline
# ожидаемо: … admin card autofill SEO/tags

sudo systemctl restart mywave-site
systemctl is-active mywave-site
# ожидаемо: active
```

**Rollback:**
```bash
cd /var/www/mywave
git checkout 4f14cecc
sudo systemctl restart mywave-site
```

---

## 2) Smoke

```bash
curl -sS -o /dev/null -w "blog %{http_code}\n" https://mywavewake.ru/blog
curl -fsS https://mywavewake.ru/health | python3 -c 'import sys,json; print(json.load(sys.stdin).get("status"))'
grep '^BLOG_ADMIN_WRITE_ENABLED=' /var/www/mywave/.env
```

---

## 3) UI (браузер)

1. `/admin/blog` → **Карточка**
2. Должны быть шаги **1. Заполнить → 2. Проверить → 3. Сохранить**
3. Кнопка **«Заполнить пустые из текста»** → появятся seo_title, теги, meta…
4. **«Сохранить в raw_feed»** → зелёный flash
5. «Открыть на сайте» — проверить карточку

«Плавающие» полупрозрачные подсказки поверх полей — часто **переводчик браузера**; отключите перевод страницы для админки.

---

## Не в этом релизе

- Редактор `final_posts` / фото-видео upload в админке → волна **B4.2** (отдельный GO)
- Camp sync / Tour — HOLD
