# S11 — Final Site Audit (light checklist)

**Дата:** 2026-07-29  
**Контекст:** после YClients CLOSED + Blog B1–B4.2  
**Camp:** HOLD  
**Команды Owner:** `docs/deploy/OWNER_S11_FULL_COMMANDS.md`

Полный S11 = этот smoke + ручная витрина + Admin GO. Не заменяет security/infra deep-dive.

---

## A. Runtime

- [x] `mywave-site` active _(S11-light 2026-07-29)_
- [x] `mywave-telegram-bot` active
- [x] `mywave-node` не трогали
- [x] Site SHA = `9b8e22f1` tip
- [x] `/health` → `status: ok`

## B. Booking boat (YClients path)

- [x] `/api/calendar/slots/<+3d>?service=boat` → HTTP 200 _(дожать: JSON — OWNER_S11_FULL)_
- [ ] Bot booking create/reschedule/cancel не регрессировал (Owner spot-check)

## C. Blog public

- [x] `/blog` 200 + 1× `og:title` + canonical _(2026-07-29)_
- [x] `/blog?q=…` 200
- [x] `/api/blog/latest` JSON
- [ ] Home `#blog` cards _(UI spot-check)_
- [ ] CSP: youtube/vk/rutube + `media-src https:` _(UI/view-source)_
- [x] Public post после B4.2: `/blog/<slug>` 200 + контент виден

## D. Blog admin B4

- [x] `/admin/blog` список
- [x] `/admin/blog/<slug>` деталка
- [ ] Invalidate cache работает _(Owner: «Сбросить кэш»)_
- [ ] Write OFF by default _(prod после B4.2 часто ON — вернуть 0 после редактуры)_
- [x] Write ON: SEO + B4.2 `final_posts`/video с confirm → Sheets OK

## E. Camp HOLD

- [x] Cron `/etc/cron.d/mywave-camp-sync` commented
- [x] Нет внезапного mass-import

## F. Editorial process

- [ ] Новые строки: ASCII slug, cover, tags — по `docs/BLOG_EDITORIAL_CHECKLIST.md`

---

## Критерий «S11 light DONE»

Все A–C базовые зелёные; D read OK; E hold подтверждён. **Выполнено 2026-07-29.**

## Критерий «S11 full DONE» (без Camp)

Блоки 0–3 и 5 в `OWNER_S11_FULL_COMMANDS.md` PASS.
