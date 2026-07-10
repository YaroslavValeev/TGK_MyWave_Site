# Camp catalog — deploy-note (Owner)

**Статус:** PR #98 в `main`. **Production deploy Site — STOP** до готовности Tour API.

**Production Site (сейчас):** `eab7eb9859054024275df8ae8a5115e1d6830c89` — **оставляем**, Online Coaching OK.

**Сервис:** только `mywave-site` (`/var/www/mywave`)  
**Не трогать:** `mywave-node`, `mywave-telegram-bot`, TGbotAdmin

---

## Merge PR #98

| Поле | Значение |
|------|----------|
| PR | [#98](https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/98) — `feat(camp): MyWaveTour MVP API contract for camp import` |
| State | **MERGED** |
| Merge commit | `75c0c792bcf3ee44b7919f29f27dcc47f4e3d96c` |
| Merged at | `2026-07-07T19:07:24Z` |
| Текущий `origin/main` (после #98) | `cdb4e59f248518575d1b275d1b0f7508f964d0b9` (+ hotfix booking #99) |

Минимальный код Camp-контракта: `75c0c792`. Рекомендуемый HEAD при deploy: актуальный `origin/main`.

---

## STOP — причины не деплоить сейчас

1. **Tour VPS:** running API-контейнер **не содержит** Camp API (`/api/v1/camps` → `Cannot GET`).
2. **Tour delivery:** **Deploy Camp API** упал на GitHub step `Docker build API preflight` (`pnpm --filter api build`). Причина: Dockerfile API не собирает workspace-зависимости `@mywave/shared-types` и `@mywave/explore-links` перед `pnpm --filter api build`. VPS **не тронут** — workflow не дошёл до upload/SSH/token rotation; `/root/CAMP_API_TOKEN.current` на Tour VPS **не должен существовать**. Ждём fix от Tour.
3. Нет подтверждённого sample: `/tmp/mywave-camps-sample.json`.
4. Нет сводки качества данных от Tour (counts: без фото / цены / booking_url / `content_rights_status=unknown`).
5. Token rotation + передача Site приватно — после готовности Tour API.

**До снятия STOP на production Site:**

- **не** выполнять `git pull origin main` на prod (до отдельного owner GO);
- **не** выполнять `flask db upgrade` под Camp;
- **не** запускать `python scripts/run_camp_sync.py`;
- **не** включать camp cron;
- **`CAMP_PUBLIC_ENABLED=0`** (публичная витрина закрыта).

### Gate для Site deploy (все пункты обязательны)

1. **Tour PR #5** merge в Tour repo.
2. Successful **Deploy Camp API** workflow на Tour VPS.
3. `GET /api/v1/camps` → envelope `{ "items": [], "next_offset": null }` (HTTP 200).
4. Bearer auth работает.
5. Снят `/tmp/mywave-camps-sample.json` (preflight с Site).
6. Token ротирован Tour и передан Site **приватно** → `MYWAVE_TOUR_CAMP_API_TOKEN` в prod `.env`.
7. Есть sample summary / сводка качества данных от Tour.
8. Отдельный **owner GO** — deploy-блок Site (этот файл § Production deploy).

---

## Контракт MyWaveTour (PR #98)

| Параметр | Значение |
|----------|----------|
| Endpoint | `https://api.mywavetour.ru/api/v1/camps` |
| Auth | `Authorization: Bearer <MYWAVE_TOUR_CAMP_API_TOKEN>` |
| Формат | `{ "items": [], "next_offset": null }` |
| Pagination | `next_offset` при `MYWAVE_TOUR_USE_API_PAGINATION=1` |
| Ошибки | 401/403/5xx/timeout → безопасный fail в import |
| Новые кемпы | `publication_status=pending_review` |
| Дубли | `possible_duplicate` |
| `content_rights_status=unknown` | не блокирует импорт, требует модерации |
| Owner camps | приоритет при публикации |

Preflight с сервера Site (когда Tour API готов):

```bash
cd /var/www/mywave
# MYWAVE_TOUR_CAMP_API_TOKEN уже в .env
./venv/bin/python scripts/check_tour_camp_api.py
# ожидание: HTTP 200, items=N, saved /tmp/mywave-camps-sample.json
```

---

## Env-переменные (добавить в `.env` на prod при GO)

```env
# Camp — staging rollout: модуль и админка ON, публикация OFF
CAMP_MODULE_ENABLED=1
CAMP_ADMIN_ENABLED=1
CAMP_PUBLIC_ENABLED=0
CAMP_IMPORT_ENABLED=1

MYWAVE_TOUR_CAMPS_API_URL=https://api.mywavetour.ru/api/v1/camps
MYWAVE_TOUR_CAMPS_FEED_URL=https://api.mywavetour.ru/camps-feed.json
MYWAVE_TOUR_CAMP_API_TOKEN=<от Tour, не коммитить>
MYWAVE_TOUR_USE_API_PAGINATION=1
```

Права:

```bash
sudo chown www-data:www-data /var/www/mywave/.env
sudo chmod 600 /var/www/mywave/.env
```

---

## Миграции БД

Revision: `d8f1a2b3c4e5` (`add_camp_tables`)  
Таблицы: `camp`, `camp_import_log`, `camp_lead`

```bash
cd /var/www/mywave
source venv/bin/activate
export FLASK_APP=main:app
flask db upgrade
flask db current   # ожидание: d8f1a2b3c4e5 (head camp chain)
```

Идемпотентно: миграция проверяет наличие таблиц перед `create_table`.

---

## Production deploy (выполнять только после GO + готовый Tour API)

```bash
set -euo pipefail
PROD_ROOT=/var/www/mywave
cd "$PROD_ROOT"
PY="$PROD_ROOT/venv/bin/python"
SERVICE_USER="${SERVICE_USER:-www-data}"

# После merge #98; при deploy позже — подставить актуальный origin/main:
EXPECTED_HEAD="cdb4e59f248518575d1b275d1b0f7508f964d0b9"

git -c safe.directory="$PROD_ROOT" fetch origin main
git -c safe.directory="$PROD_ROOT" checkout main
git -c safe.directory="$PROD_ROOT" pull --ff-only origin main
test "$(git -c safe.directory="$PROD_ROOT" rev-parse HEAD)" = "$EXPECTED_HEAD"

sudo mkdir -p "$PROD_ROOT/logs" "$PROD_ROOT/instance"
sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$PROD_ROOT/logs" "$PROD_ROOT/instance"

source venv/bin/activate
pip install -r requirements.txt -q
export FLASK_APP=main:app
flask db upgrade

# Preflight Tour API (обязательно перед первым sync):
"$PY" scripts/check_tour_camp_api.py

sudo systemctl restart mywave-site
sleep 12
curl -sf https://mywavewake.ru/health/live && echo " HEALTH OK"
```

---

## Первый sync (только после preflight OK)

```bash
cd /var/www/mywave
sudo -u www-data ./venv/bin/python scripts/run_camp_sync.py
# или: flask camp-sync
```

Ожидание в stdout: `camp_sync: {'fetched': N, 'created': ..., ...}`  
Импортированные записи — в админке `/admin/camp/`, статус `pending_review`.

**Публичный раздел `/projects/camp` остаётся 404**, пока `CAMP_PUBLIC_ENABLED=0`.

---

## Smoke (после deploy + sync)

```bash
cd /var/www/mywave
source venv/bin/activate
pytest tests/unit/test_camp_import.py tests/unit/test_camp_public_api.py -q

curl -s -o /dev/null -w "%{http_code}\n" https://mywavewake.ru/admin/camp/
# 302 (login) или 200

curl -s -o /dev/null -w "%{http_code}\n" https://mywavewake.ru/projects/camp
# 404 пока CAMP_PUBLIC_ENABLED=0

curl -s -o /dev/null -w "%{http_code}\n" https://mywavewake.ru/api/camps
# 404 или пустой список — зависит от флагов
```

Модерация: опубликовать выбранные кемпы в `/admin/camp/<id>` → только потом:

```bash
# в .env: CAMP_PUBLIC_ENABLED=1
sudo systemctl restart mywave-site
curl -sf https://mywavewake.ru/projects/camp | head -c 200
```

---

## Cron (не включать до стабильного импорта)

Пример (каждые 6 ч) — **отложено**:

```cron
0 */6 * * * cd /var/www/mywave && ./venv/bin/python scripts/run_camp_sync.py >> logs/camp_sync.log 2>&1
```

Добавлять в `sudo crontab -u www-data -e` только после approve владельца.

---

## Rollback

```bash
cd /var/www/mywave
git -c safe.directory=/var/www/mywave checkout eab7eb9859054024275df8ae8a5115e1d6830c89
# в .env: CAMP_MODULE_ENABLED=0 CAMP_IMPORT_ENABLED=0 CAMP_PUBLIC_ENABLED=0
source venv/bin/activate
export FLASK_APP=main:app
# downgrade только если таблицы пустые и есть approve:
# flask db downgrade c4e8f1a2b3d0
sudo systemctl restart mywave-site
curl -sf https://mywavewake.ru/health/live
```

Rollback-point до Camp PR #98: `eab7eb98` (Online Coaching + `run_camp_sync.py` без контракта #98).

---

## Чеклист готовности к production Camp

- [ ] Tour deploy: `GET /api/v1/camps` → 200 + `{items, next_offset}`
- [ ] `check_tour_camp_api.py` → OK с prod Site
- [ ] Sample `/tmp/mywave-camps-sample.json` + сводка качества от Tour
- [ ] Owner GO на production deploy Site
- [ ] `flask db upgrade` на prod
- [ ] Первый `run_camp_sync.py`, записи в `pending_review`
- [ ] Ручная модерация в `/admin/camp/`
- [ ] `CAMP_PUBLIC_ENABLED=1` — отдельное решение владельца
- [ ] Cron — отдельное решение после стабильного импорта
