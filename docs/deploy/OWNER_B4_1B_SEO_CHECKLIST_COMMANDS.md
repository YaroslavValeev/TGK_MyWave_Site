# Owner — B4.1b SEO checklist + улучшенные теги MyWave

**Сервис:** только `mywave-site`  
**Флаг:** `BLOG_ADMIN_WRITE_ENABLED=1` (уже)

---

## 1) Deploy

```bash
cd /var/www/mywave
git pull --ff-only origin main
git log -1 --oneline
# ожидаемо: … SEO checklist / MyWave taxonomy

sudo systemctl restart mywave-site
systemctl is-active mywave-site
```

**Rollback:**
```bash
cd /var/www/mywave
git checkout 74fafb0e
sudo systemctl restart mywave-site
```

---

## 2) Smoke

```bash
curl -sS -o /dev/null -w "blog %{http_code}\n" https://mywavewake.ru/blog
systemctl is-active mywave-site
grep '^BLOG_ADMIN_WRITE_ENABLED=' /var/www/mywave/.env
```

---

## 3) UI

1. `/admin/blog` → Карточка  
2. Блок **«SEO-оценка карточки: N/100»** с ✓ / ! / ✕  
3. **Заполнить пустые из текста** → score обновляется  
4. При критичных fail: save блокируется, пока не исправите **или** чекбокс «Сохранить несмотря на…»  
5. Успешный save → flash с `SEO N/100`

Это **редакторский чеклист**, не замена SEO-специалиста. Полный редактор текста/медиа = отдельная волна B4.2.
