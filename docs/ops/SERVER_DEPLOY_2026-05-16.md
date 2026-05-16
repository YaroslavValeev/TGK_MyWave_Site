# Деплой на сервер — один блок команд (2026-05-16)

**Прод:** https://mywavewake.ru  
**Runtime FROZEN** — только `git pull`, `restart`, static, frontend templates.

После `git push` с ПК выполните на SSH **целиком**:

```bash
set -e
cd /var/www/mywave

echo "=== 1. Код ==="
git fetch origin main
git pull --ff-only origin main
git log -3 --oneline

echo "=== 2. Restart (шаблоны: mobile-home, отзывы ?v=2, checklist cardbg13) ==="
sudo systemctl restart mywave-site
sleep 3

echo "=== 3. Фото учеников (отзывы) — размер файла ==="
curl -sSI https://mywavewake.ru/static/images/students/Elya_Vesnina.jpg | grep -E 'HTTP|Content-Length'
# ожидается: 200, Content-Length около 126065 (не 319136)

echo "=== 4. Mobile home v3 ==="
curl -sS --compressed -L https://mywavewake.ru/ | grep -F mobile-home

echo "=== 5. Checklist assets ==="
find static/images/Project/Cards/checklist -name '*.webp' | wc -l
# ожидается: 55
curl -sS -o /dev/null -w 'checklist webp: %{http_code}\n' \
  https://mywavewake.ru/static/images/Project/Cards/checklist/app/app_event_information.webp

echo "=== 6. QA scripts ==="
bash scripts/qa_mobile_precheck.sh
bash scripts/production_smoke.sh

echo "=== DONE ==="
echo "Браузер: главная Ctrl+F5 — отзывы с фото; /projects/checklist-org — cardbg13"
```

## Проверка в браузере

| Страница | Что смотреть |
|----------|----------------|
| `/` | Отзывы — круглые **фото** учеников (не эскиз, не логотип) |
| `/` | Network: `.../students/*.jpg?v=2` → 200 |
| `/projects/checklist-org` | Справа в карточке `<img class="wake-checklist__card-art-img">`, `data-checklist-bg="ok"` |

## Если checklist — только градиенты

Файлы в git — **placeholder webp ~2 KB**. Финальные иллюстрации положить в  
`static/images/Project/Cards/checklist/` (имена как в `checklist.js`), затем снова `git pull` на сервере.
