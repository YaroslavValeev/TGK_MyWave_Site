# Owner — Blog B1/B3 deploy + verify

**Статус prod:** **CLOSED / PASS** (2026-07-29, SHA `d1fe85ed`)

| Check | Result |
|-------|--------|
| SHA | `d1fe85ed` |
| `/blog` | HTTP 200 |
| `og:title` count | **1** (`Блог MyWave — новости и статьи`) |
| canonical | `https://mywavewake.ru/blog` |
| `?q=foil` | 200 |
| API latest slug | ASCII (`1-avgusta-v-klube-…-fc2213`) |
| CSP `frame-src` | youtube + vk + rutube + ok + kinescope |
| CSP `media-src` | `'self' blob: https: http:` |

**Ожидаемо из Sheets (не баг сайта):** `tags: []`, `video_url: null` — править в Parser/`raw_feed` по `docs/BLOG_EDITORIAL_CHECKLIST.md`.

---

## Rollback (если понадобится)

```bash
cd /var/www/mywave
git checkout c70b13f6
sudo systemctl restart mywave-site
```

---

## Дальше

| Волна | Статус |
|-------|--------|
| YClients S5–S10 | CLOSED |
| Blog B2 SEO | CLOSED |
| Blog B1 + B3 | **CLOSED** |
| B4 Admin write | pending GO |
| S11 Final audit | after B4 / GO |
| Camp | HOLD |
