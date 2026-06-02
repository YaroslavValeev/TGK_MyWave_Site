# BOOKING_PHASE2_STAGING_SMOKE.md

**Scope:** Site Phase 2 booking (после merge PR-серии, **до** production rollout)  
**Environment:** staging / pre-prod с `BOOKING_PHASE2_*=1`  
**Participants:** Site + TGbotAdmin (production Telegram/admin account, Calendar, Sheets)  
**Contract review:** ✅ завершён (2026-06-01)

---

## 0. Preconditions

- [ ] Contract v2 + Availability v1 signed off TGbotAdmin
- [ ] Phase 1 production **не** затронут (flags OFF on prod)
- [ ] Staging `mywave-site` restarted after deploy
- [ ] `GOOGLE_CALENDAR_ID` / `SPREADSHEET_ID` — staging или isolated test calendar (preferred)

---

## 1. Feature flags on staging

```bash
BOOKING_PHASE2_AVAILABILITY=1
BOOKING_PHASE2_MULTI_SET_BOAT=1
BOOKING_PHASE2_TRAVEL_BUFFER=1
BOOKING_PHASE2_SUMMARY_V2=1
BOOKING_PHASE2_GYM_LOCATION_V2=1
```

---

## 2. Regression — Phase 1 paths (flags OFF smoke on staging clone)

- [ ] Gym single booking: 1 event, 90 min, summary v1 OR v2 per flag
- [ ] Boat single set: 1 event, 30 min
- [ ] `test_booking_phase1.py` — all pass
- [ ] `test_public_routes_p0.py` — all pass
- [ ] Path B (`sheets.book_slot`) uses same pipeline

---

## 3. Gym (Phase 2)

- [ ] Slots API: `remaining` из Calendar occupancy (`max_capacity: 4`)
- [ ] Slot available при 1/4, 2/4, 3/4; hidden/disabled при 4/4
- [ ] Web booking создаёт 1 event: `end = start + 90 min` (при `occupancy < 4`)
- [ ] Summary (v2): `Тренировка — Зал — <Имя> (WEB_ID: …)`
- [ ] Location: `Зал`
- [ ] Confirmation UX: coords `55.777052, 37.502594`, map `https://yandex.ru/maps/-/CLWQy6-I`
- [ ] Sheets: 1 Workouts + 1 Client_Workouts, status `подтверждено`
- [ ] Duplicate submit → no second event

---

## 3b. Gym — group capacity (4/4)

- [ ] 3 клиента на slot 10:00 → API `remaining: 1`, book OK
- [ ] 4-й клиент → book OK, затем slot unavailable
- [ ] 5-й concurrent book → 409 / «нет мест»
- [ ] Несколько gym Calendar events на один `[T, T+90)` — ожидаемое поведение

---

## 4. Boat — single set (exclusive)

- [ ] 1 event, 30 min; **1 клиент** на slot
- [ ] Второй клиент на тот же 30-min slot → blocked
- [ ] Summary (v2): `Тренировка — Катер — 1 сет — …`
- [ ] Location: MyWave Wake Yandex URL (v1)
- [ ] `workout_id = event.id`

---

## 5. Boat — multi-set (N>1, exclusive range)

- [ ] UI/API: select N adjacent sets (e.g. 3)
- [ ] **1 continuous Calendar event** (not N events)
- [ ] `end = start + N×30 min`
- [ ] Занятый диапазон 18:00–19:00 блокирует 18:00 и 18:30 для других клиентов
- [ ] Summary: `Тренировка — Катер — 3 сета — …`
- [ ] `extendedProperties.private.set_count = N`
- [ ] Sheets Workouts: 1 row, duration = N×30
- [ ] Non-adjacent selection rejected

---

## 6. Travel buffer (2h gym ↔ boat)

- [ ] Existing boat 12:00–12:30 → gym slot before 14:30 hidden/blocked
- [ ] Existing gym 10:00–11:30 → boat before 13:30 hidden/blocked
- [ ] Allowed slots after buffer still bookable

---

## 7. Availability / pre-confirm recheck

- [ ] Book last free slot → success
- [ ] Simulate concurrent booking (bot or manual Calendar insert) → Site returns conflict, **no** orphan Sheets row
- [ ] Full-day Calendar scan includes buffer window

---

## 8. TGbotAdmin cross-smoke

- [ ] Existing TG event `(ID: tg_id)` unchanged; bot antid dup still works
- [ ] Web event `(WEB_ID: …)` visible in Calendar; bot does not mis-parse as Telegram ID
- [ ] Bot-side booking after web booking respects shared calendar occupancy
- [ ] No regression in bot duration/location for Telegram path

---

## 9. Logs (no PII)

- [ ] `availability_check`, `booking_calendar_event_created`, `booking_duplicate_detected`
- [ ] No raw phone in journalctl / app logs

---

## 10. Production rollout gate

Staging smoke **all green** → Owner approves prod flags rollout (one flag at a time):

1. `BOOKING_PHASE2_AVAILABILITY`
2. `BOOKING_PHASE2_TRAVEL_BUFFER`
3. `BOOKING_PHASE2_MULTI_SET_BOAT`
4. `BOOKING_PHASE2_SUMMARY_V2` + `BOOKING_PHASE2_GYM_LOCATION_V2`

Each step: restart **only** `mywave-site`, curl/API smoke, 24h watch.

---

## 11. Rollback

Set all `BOOKING_PHASE2_*=0` → restart `mywave-site` → Phase 1 behavior restored.

No data migration required for rollback (existing Calendar events remain valid).
