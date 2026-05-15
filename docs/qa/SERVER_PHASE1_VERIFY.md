# Phase 1 — команды на сервере (после `git push` с ПК)

**Цель:** `PRECHECK OK` + подтверждение `mobile-home.css?v=3` в HTML.  
**Runtime FROZEN** — только `git pull`, `restart` при необходимости, скрипты QA.  
**Коммиты с фиксом precheck:** `76b1c82f`, `dc08c500` (проверка HTML **до** остальных curl).

---

## 1. Обновить код

```bash
cd /var/www/mywave
git fetch origin main
git pull --ff-only origin main
git log -1 --oneline
# ожидается: dc08c500 или новее
```

---

## 2. Шаблон и restart (если ещё не делали сегодня)

```bash
grep mobile-home templates/base.html
# ожидается: ...mobile-home.css...?v=3

sudo systemctl restart mywave-site
sleep 3
```

---

## 3. Ручная проверка HTML (канон)

```bash
curl -sS --compressed -L https://mywavewake.ru/ | grep -F mobile-home
```

Ожидается:

```html
<link rel="stylesheet" href="/static/css/mobile-home.css?v=3" />
```

---

## 4. Автоматический precheck + smoke

```bash
bash scripts/qa_mobile_precheck.sh
bash scripts/production_smoke.sh
```

Ожидается в конце precheck:

```text
OK   html_links_mobile_home_css
OK   html_mobile_home_version  v=3
...
PRECHECK OK — proceed with manual device QA (A1/A2/I1/T1)
```

---

## 5. Если precheck FAIL, а ручной curl OK

- Убедитесь, что на сервере **новый** скрипт (HTML проверяется **в начале** файла, не после `_check home`).
- `head -30 scripts/qa_mobile_precheck.sh` — должна быть строка `HOME_HTML="$(curl -sS --compressed` сразу после заголовка.
- Снова `git pull` с ПК, где выполнен `git push origin main`.

---

## 6. Step 1 — только на устройствах (владелец)

| ID | Платформа |
|----|-----------|
| A1 | Android Chrome |
| A2 | Android Yandex |
| I1 | iPhone Safari |
| T1 | Tablet |

Инкогнито · hard refresh · скриншоты → `docs/qa/screenshots/2026-05-15/`  
Заполнить: [MOBILE_QA_RUN_2026-05-15.md](MOBILE_QA_RUN_2026-05-15.md), [MOBILE_QA_MATRIX.md](MOBILE_QA_MATRIX.md)

Статус: [PHASE1_MOBILE_QA_STATUS.md](PHASE1_MOBILE_QA_STATUS.md)
