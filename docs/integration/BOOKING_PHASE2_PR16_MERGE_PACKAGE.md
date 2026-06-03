# BOOKING_PHASE2_PR16 — Merge / Release Package

**PR:** #16 — Pipeline recheck + writer v2 + idempotency range + 409  
**Branch:** `feature/booking-phase2-pr3-pipeline-writer`  
**PR link:** https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/16  

| Commit | Hash | Note |
|--------|------|------|
| **HEAD (re-review)** | `9004d3bbdb9858bb9ba43e59541da4a0d42fc76a` | TGbotAdmin blocker fixes |
| Previous | `116af0d563574ae78267b637c453dcadfb724e2b` | Initial PR3 implementation |

**CI:** green (`quality-checks` pass on `9004d3bb`)  
**Tests:** `75 passed`  
**GM status:** **READY FOR TGBOTADMIN RE-REVIEW**  

**Policy:** merge/deploy **только после** TGbotAdmin PASS + отдельное GM merge approval; **flags OFF** на prod.

**Не выполнялось:** merge, production deploy, restart `mywave-site` / node / bot, prod `.env`, prod flags ON.

---

## 0. TGbotAdmin review

| Round | Result | Commit |
|-------|--------|--------|
| 1 | **CHANGES REQUESTED** — merge blocked | `116af0d5` |
| 2 | ⏳ **PENDING** re-review | `9004d3bb` |

### Blocker fixes (round 2 — Site)

| Blocker | Fix | Verified |
|---------|-----|----------|
| **1 Boat location v2** | `calendar_location_v2: "Катер"`; `get_calendar_location("boat")` при `BOOKING_PHASE2_GYM_LOCATION_V2=1` | tests `test_boat_location_v2_*` |
| **2 Calendar buffer window** | `day_bounds_with_buffer(±120)` в `list_busy_intervals_for_date` при `BOOKING_PHASE2_AVAILABILITY=1` | `test_booking_calendar_reader_buffer.py` |

**Flags OFF:** boat location остаётся Phase 1 `MyWave Wake — ...`.

**Checklist для TGbotAdmin (round 2):**

- [ ] Blocker 1: boat `location: Катер` при location v2 flag
- [ ] Blocker 2: `timeMin`/`timeMax` ±120 min; cross-day buffer conflicts
- [ ] `assert_booking_available()` до Calendar insert
- [ ] Conflict → no Calendar insert, no orphan Sheets
- [ ] HTTP 409, WEB_ID / ID separation
- [ ] Writer v2, range idempotency, flags OFF regression

---

## 0.1 Non-blocker risks (Owner decision до staging / prod flags)

### Risk 1 — Boat slot grid mismatch

| Система | Boat grid (local day) |
|---------|------------------------|
| **Site** | `06:00` – `21:00` (`availability.py` `BOAT_GRID_START` / `BOAT_GRID_END`) |
| **TGbotAdmin** | `07:00` – `19:30` (per TGbotAdmin contract) |

**Impact:** GET slots и POST validation могут расходиться между Site web и Telegram bot на краях сетки.

**Decision required (до staging E2E):**

- **A)** Синхронизировать grids (Site → TGbotAdmin window или наоборот, по Owner); **или**
- **B)** Явно принять расхождение в joint smoke с documented edge cases (06:00–07:00, 19:30–21:00).

**PR #16:** grid **не** меняли (out of blocker scope).

---

### Risk 2 — Partial Sheets failure

**Сценарий:** `write_workout_row()` успешен, `write_client_workout_row()` падает → возможна orphan строка в **Workouts** без **Client_Workouts**.

**Покрыто сейчас:**

| Path | Поведение |
|------|-----------|
| Failed final recheck | No Calendar, no Sheets |
| Calendar insert fail | No Sheets |

**Не покрыто:** partial success внутри Sheets phase после успешного Calendar.

**Site position:** **accepted risk for PR #16**; compensation (transaction / rollback row / repair job) — **follow-up до production flags ON**, не blocker merge.

**Mitigation (ops):** при инциденте — ручная чистка orphan `Workouts` по `workout_id` без пары в `Client_Workouts`.

---

## 1. Merge status

| Поле | Значение |
|------|----------|
| **PR #16 merged** | ⏳ NO |
| **Next gate** | TGbotAdmin round 2 PASS → GM merge approval |

### Changed files (full PR #16)

```
app/config/booking_venues.py
app/services/booking/pipeline.py
app/services/booking/availability.py
app/services/booking/calendar_writer.py
app/services/booking/calendar_reader.py
app/services/booking/idempotency.py
app/services/booking/sheets_writer.py
app/services/booking/__init__.py
app/routes/calendar_routes.py
app/schemas/__init__.py
app/modules/sheets.py
tests/unit/test_booking_calendar_v2.py              (new)
tests/unit/test_booking_pipeline_phase2.py          (new)
tests/unit/test_booking_calendar_reader_buffer.py     (new)
docs/integration/BOOKING_PHASE2_PR16_MERGE_PACKAGE.md (new)
```

**Не входит:** `static/js/booking.js` (PR4), prod `.env`, `mywave-node`, `mywave-telegram-bot`, TGbotAdmin code.

---

## 2. Production impact

| Утверждение | Статус |
|-------------|--------|
| POST pipeline при flags OFF | **Phase 1** |
| Writer v2 / 409 / buffer / range idempotency | **только при flags ON** |
| Все `BOOKING_PHASE2_*` default OFF | **YES** |
| Restart при deploy | **только `mywave-site`** |
| Phase 2 booking complete | **NO** (PR4 + staging E2E + flags approval) |

---

## 3. CI / test evidence

```bash
python -m pytest tests/unit/test_booking_availability_phase2.py \
  tests/unit/test_booking_features.py \
  tests/unit/test_booking_phase1.py \
  tests/unit/test_boat_slots.py \
  tests/unit/test_booking_calendar_v2.py \
  tests/unit/test_booking_pipeline_phase2.py \
  tests/unit/test_booking_calendar_reader_buffer.py -q
```

**Ожидается:** `75 passed`

---

## 4. Production release commands (flags OFF)

**Только после TGbotAdmin PASS + GM merge approval.**

```bash
sudo MYWAVE_ROOT=/var/www/mywave bash /var/www/mywave/deploy/scripts/backup_mywave.sh

cd /var/www/mywave
git fetch --all --prune
git checkout main
git pull --ff-only origin main

grep -E '^BOOKING_PHASE2_' .env || echo "OK: no BOOKING_PHASE2_* in .env"

source venv/bin/activate
export SECRET_KEY="${SECRET_KEY:-$(grep -E '^SECRET_KEY=' .env | cut -d= -f2-)}"

python -m pytest tests/unit/test_booking_availability_phase2.py \
  tests/unit/test_booking_features.py \
  tests/unit/test_booking_phase1.py \
  tests/unit/test_boat_slots.py \
  tests/unit/test_booking_calendar_v2.py \
  tests/unit/test_booking_pipeline_phase2.py \
  tests/unit/test_booking_calendar_reader_buffer.py -q

sudo systemctl restart mywave-site
```

**НЕ выполнять:**

```bash
sudo systemctl restart mywave-node.service
sudo systemctl restart mywave-telegram-bot.service
```

---

## 5. Rollback

| Сценарий | Действие |
|----------|----------|
| Pre-PR16 prod | `4584cc87c0593ec67dd3dae8a069eadd62eac01c` (PR #15) |
| Post-deploy revert | `git revert <merge-commit>` + pytest + `restart mywave-site` only |

---

## 6. Post-deploy smoke (flags OFF)

```bash
sudo systemctl is-active mywave-site
curl -fsS https://mywavewake.ru/health
curl -fsS -o /dev/null -w "home %{http_code}\n" https://mywavewake.ru/
```

Phase 1 booking sanity — без включения `BOOKING_PHASE2_*`.

---

## 7. После TGbotAdmin PASS

1. GM merge approval → merge PR #16  
2. Deploy §4 (flags OFF)  
3. Staging E2E + grid decision (Risk 1)  
4. PR4 frontend  
5. Phased prod flags ON (отдельное approval; Risk 2 follow-up желателен до flags ON)

---

## 8. Site confirmations (заполнить после TGbotAdmin round 2)

- [ ] TGbotAdmin: **PASS** / changes requested  
- [ ] GM merge approval  
- [ ] Restart **только** `mywave-site`  
- [ ] **Не** restart node / telegram-bot  
- [ ] Production flags **OFF**  
- [ ] Risk 1 (grid): Owner decision recorded  
- [ ] Risk 2 (partial Sheets): accepted / follow-up ticket  
