# BOOKING_PHASE2_PR16 — Merge / Release Package (draft)

**PR:** #16 — Pipeline recheck + writer v2 + idempotency range + 409  
**Branch:** `feature/booking-phase2-pr3-pipeline-writer`  
**Commit (HEAD feature):** `116af0d563574ae78267b637c453dcadfb724e2b`  
**CI:** green (`quality-checks` pass)  
**Local tests:** `69 passed`  
**Policy:** merge/deploy **только после** TGbotAdmin review + отдельное GM merge approval; **flags OFF** на prod.

---

## 0. TGbotAdmin review

| Поле | Значение |
|------|----------|
| **TGbotAdmin result (round 1)** | **CHANGES REQUESTED** — merge blocked |
| **Blocker 1** | Boat `location` v2 → canonical `Катер` при `BOOKING_PHASE2_GYM_LOCATION_V2=1` |
| **Blocker 2** | Calendar list window ±120 min при `BOOKING_PHASE2_AVAILABILITY=1` |
| **Round 2** | ⏳ PENDING re-review после fix commit |

### Non-blocker risks (зафиксировано)

| Risk | Статус |
|------|--------|
| **Boat slot grid** Site 06:00–21:00 vs TGbotAdmin 07:00–19:30 | Синхронизация или явное подтверждение расхождения **до staging E2E** |
| **Partial Sheets failure** | `write_workout_row` OK + `write_client_workout_row` fail → возможен orphan Workouts row; компенсация/transaction — **post-PR16** (risk note only) |

**Checklist для TGbotAdmin:**

- [ ] `assert_booking_available()` вызывается **до** Calendar insert (при `BOOKING_PHASE2_AVAILABILITY=1`)
- [ ] При conflict **нет** `events.insert`
- [ ] При conflict **нет** orphan Sheets (Workouts / Client_Workouts)
- [ ] HTTP **409** с понятным телом (gym vs boat)
- [ ] WEB_ID `(WEB_ID: …)` не смешивается с Telegram `(ID: tg_id)`
- [ ] Writer v2: summary / location / duration / `set_count` / continuous multi-set boat
- [ ] Idempotency: continuous range (phone + date + start + end + service)
- [ ] Flags OFF: Phase 1 regression без изменений

---

## 1. Merge status

| Поле | Значение |
|------|----------|
| **PR #16 merged** | ⏳ NO — ждём TGbotAdmin + GM merge approval |
| **PR link** | https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/16 |

### Final changed files (11)

```
app/services/booking/pipeline.py
app/services/booking/availability.py
app/services/booking/calendar_writer.py
app/services/booking/idempotency.py
app/services/booking/sheets_writer.py
app/services/booking/__init__.py
app/routes/calendar_routes.py
app/schemas/__init__.py
app/modules/sheets.py
tests/unit/test_booking_calendar_v2.py          (new)
tests/unit/test_booking_pipeline_phase2.py      (new)
```

**Не входит:** `static/js/booking.js` (PR4), prod `.env`, systemd node/bot, TGbotAdmin code.

---

## 2. Production impact

| Утверждение | Статус |
|-------------|--------|
| POST pipeline при flags OFF | **Phase 1** (без recheck v2, point idempotency) |
| Writer v2 / 409 / range idempotency | **только при flags ON** |
| Все `BOOKING_PHASE2_*` default OFF | **YES** |
| `mywave-node.service` | **не трогаем** |
| `mywave-telegram-bot.service` | **не трогаем** |
| Restart при deploy | **только `mywave-site`** |
| Phase 2 booking complete | **NO** (PR4 UI + staging E2E + prod flags approval) |

---

## 3. CI / test evidence

**CI (PR #16):** `quality-checks` — pass.

**Канон (после merge в `main`, на сервере):**

```bash
cd /var/www/mywave
source venv/bin/activate
export SECRET_KEY="${SECRET_KEY:-$(grep -E '^SECRET_KEY=' .env | cut -d= -f2-)}"

python -m pytest tests/unit/test_booking_availability_phase2.py \
  tests/unit/test_booking_features.py \
  tests/unit/test_booking_phase1.py \
  tests/unit/test_boat_slots.py \
  tests/unit/test_booking_calendar_v2.py \
  tests/unit/test_booking_pipeline_phase2.py -q
```

**Ожидается:** `69 passed`

**Flags default OFF:**

```bash
grep -E '^BOOKING_PHASE2_' .env || echo "OK: no BOOKING_PHASE2_* in .env"
python -c "from app.config.booking_features import get_booking_phase2_flags; print(get_booking_phase2_flags())"
# все False при отсутствии env
```

---

## 4. Production release commands (flags OFF)

**Выполнять только после GM merge approval.**

```bash
sudo MYWAVE_ROOT=/var/www/mywave bash /var/www/mywave/deploy/scripts/backup_mywave.sh

cd /var/www/mywave
git fetch --all --prune
git checkout main
git pull --ff-only origin main

git rev-parse HEAD
# ожидается: merge commit PR #16 (после merge)

grep -E '^BOOKING_PHASE2_' .env || echo "OK: no BOOKING_PHASE2_* in .env"

source venv/bin/activate
export SECRET_KEY="${SECRET_KEY:-$(grep -E '^SECRET_KEY=' .env | cut -d= -f2-)}"

python -m pytest tests/unit/test_booking_availability_phase2.py \
  tests/unit/test_booking_features.py \
  tests/unit/test_booking_phase1.py \
  tests/unit/test_boat_slots.py \
  tests/unit/test_booking_calendar_v2.py \
  tests/unit/test_booking_pipeline_phase2.py -q

sudo systemctl restart mywave-site
```

**НЕ выполнять:**

```bash
sudo systemctl restart mywave-node.service
sudo systemctl restart mywave-telegram-bot.service
```

**НЕ добавлять в `.env` без отдельного approval:**

```bash
BOOKING_PHASE2_AVAILABILITY=1
BOOKING_PHASE2_TRAVEL_BUFFER=1
BOOKING_PHASE2_MULTI_SET_BOAT=1
BOOKING_PHASE2_SUMMARY_V2=1
BOOKING_PHASE2_GYM_LOCATION_V2=1
```

---

## 5. Rollback plan

| Сценарий | Действие |
|----------|----------|
| До merge | закрыть / не мержить PR #16 — prod на `4584cc87` (PR #15) |
| После deploy | `git revert <merge-commit>` на `main` + pull prod + pytest + `restart mywave-site` |
| Runtime OFF | все `BOOKING_PHASE2_*` absent/`0` — поведение Phase 1 |

**Rollback commit (pre-PR16 prod):** `4584cc87c0593ec67dd3dae8a069eadd62eac01c`

---

## 6. Post-deploy smoke (flags OFF)

Подождать **5–10 сек** после restart:

```bash
sudo systemctl is-active mywave-site
curl -fsS https://mywavewake.ru/health
curl -fsS -o /dev/null -w "home %{http_code}\n" https://mywavewake.ru/

# Phase 1 booking sanity (no flags): GET slots + optional test POST on staging only
```

**Ожидается:** `mywave-site` active, health/home `200`, booking POST без регрессии Phase 1.

---

## 7. Writer / conflict examples (staging, flags ON — не prod)

| Case | Пример |
|------|--------|
| Зал | `Тренировка — Зал — Иван (WEB_ID: bk_…)`, 90 min |
| Катер 1 сет | `… 1 сет …`, 30 min, `set_count: "1"` |
| Катер 3 сета | один event 90 min, `… 3 сета …`, `set_count: "3"` |
| WEB_ID | `(WEB_ID: bk_…)` — не `(ID: tg_id)` |
| 409 | HTTP 409, нет Calendar event, нет Sheets rows |

---

## 8. После deploy PR16

1. Staging E2E — `docs/integration/BOOKING_PHASE2_PR3_IMPLEMENTATION_PACKAGE.md` §6  
2. PR4 — `static/js/booking.js` (multi-set UI)  
3. Отдельное GM approval — phased prod flags ON  

---

## 9. Site confirmations (для финального сообщения GM)

- [ ] TGbotAdmin review: PASS / changes requested  
- [ ] Merge PR #16 — только по отдельному GM approval  
- [ ] Restart **только** `mywave-site`  
- [ ] **Не** restart `mywave-node.service`  
- [ ] **Не** restart `mywave-telegram-bot.service`  
- [ ] Production flags **OFF** by default  
