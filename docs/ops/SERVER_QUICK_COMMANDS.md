# Сервер — быстрые команды (deploy only)

**Правило:** на production **не** `git commit` / **не** `git push`. Только `git pull` + restart.

**Прод:** https://mywavewake.ru

---

## Стандартный deploy (после push с ПК)

```bash
cd /var/www/mywave
git fetch origin main
git pull --ff-only origin main
sudo systemctl restart mywave-site
sleep 2
sudo systemctl is-active mywave-site
```

Проверка:

```bash
bash scripts/verify_production_frontend.sh
bash scripts/production_smoke.sh
```

---

## Checklist — проверка art (placeholder vs final)

```bash
curl -sS -o /dev/null -w 'checklist webp bytes: %{size_download}\n' \
  'https://mywavewake.ru/static/images/Project/Cards/checklist/aquatory/aquatory_types_comparison.webp'
```

| Байт | Значение |
|------|----------|
| < 8 000 | placeholder (нужен art от дизайна) |
| > 20 000 | финальный art, вероятно OK |

Страница: https://mywavewake.ru/projects/checklist-org — **Ctrl+F5**.

---

## Блог — smoke (опционально)

```bash
cd /var/www/mywave
source venv/bin/activate
set -a && source .env && set +a
python scripts/blog_raw_feed_smoke_check.py
curl -sS 'https://mywavewake.ru/api/blog/posts?limit=3'
```

---

## Если на сервере «грязный» git status

Не коммитить с сервера. На ПК синхронизировать art → push; на сервере:

```bash
cd /var/www/mywave
git stash push -m "server-local" -- app/view.py 2>/dev/null || true
git pull --ff-only origin main
sudo systemctl restart mywave-site
```
