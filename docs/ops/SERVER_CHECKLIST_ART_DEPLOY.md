# Сервер: выкладка финальных checklist webp

**Прод:** https://mywavewake.ru/projects/checklist-org  
**Проверка placeholder vs final:** `curl` → размер файла **> 20000** байт ≈ final; **< 8000** ≈ placeholder.

---

## Вариант A — art уже на сервере, commit с сервера (один раз)

```bash
cd /var/www/mywave

git config --global user.email "mywavegithub1@yandex.ru"
git config --global user.name "mywaveguthub1"

git status --short static/images/Project/Cards/checklist/

git add static/images/Project/Cards/checklist/
git commit -m "assets(checklist): final card illustrations"

git push origin main
# Username: YaroslavValeev
# Password: <GitHub Personal Access Token, не пароль аккаунта>

sudo systemctl restart mywave-site
```

Проверка:

```bash
curl -sS -o /dev/null -w 'webp bytes: %{size_download}\n' \
  'https://mywavewake.ru/static/images/Project/Cards/checklist/aquatory/aquatory_types_comparison.webp'

bash scripts/verify_production_frontend.sh
```

---

## Вариант B — commit с ПК, на сервере только pull (предпочтительно)

На **Windows (ПК)** после копирования webp в `static/images/Project/Cards/checklist/`:

```powershell
cd "f:\Проекты MyWave\Site_MyWave"
git add static/images/Project/Cards/checklist/
git commit -m "assets(checklist): final card illustrations"
git push origin main
```

На **сервере:**

```bash
cd /var/www/mywave
git pull --ff-only origin main
sudo systemctl restart mywave-site

curl -sS -o /dev/null -w 'webp bytes: %{size_download}\n' \
  'https://mywavewake.ru/static/images/Project/Cards/checklist/aquatory/aquatory_types_comparison.webp'
```

---

## Если push с сервера не нужен (только локальный pull на прод)

Если commit на сервере **не прошёл**, а файлы уже лежат в `static/...`:

```bash
cd /var/www/mywave
# не делать git reset — файлы останутся на диске
sudo systemctl restart mywave-site
curl -sS -o /dev/null -w 'webp bytes: %{size_download}\n' \
  'https://mywavewake.ru/static/images/Project/Cards/checklist/aquatory/aquatory_types_comparison.webp'
```

Сайт отдаст новые файлы **даже без commit**, но при следующем `git pull` их может затереть старая версия из Git — **обязательно** довести commit до `origin/main`.

---

## Браузер

https://mywavewake.ru/projects/checklist-org — **Ctrl+F5** (incognito).

---

## Синхронизация ПК после push с сервера

```powershell
cd "f:\Проекты MyWave\Site_MyWave"
git pull --ff-only origin main
```
