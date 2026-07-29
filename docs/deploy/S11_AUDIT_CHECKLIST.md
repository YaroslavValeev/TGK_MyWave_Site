# S11 — Final Site Audit (light checklist)

**Дата:** 2026-07-29  
**Контекст:** после YClients CLOSED + Blog B1–B4  
**Camp:** HOLD  

Полный S11 = этот smoke + ручная витрина + Admin GO. Не заменяет security/infra deep-dive.

---

## A. Runtime

- [ ] `mywave-site` active
- [ ] `mywave-telegram-bot` active
- [ ] `mywave-node` не трогали
- [ ] Site SHA = ожидаемый main tip
- [ ] `/health` → `status: ok`

## B. Booking boat (YClients path)

- [ ] `/api/calendar/slots/<+3d>?service=boat` → JSON slots
- [ ] Bot booking create/reschedule/cancel не регрессировал (Owner spot-check)

## C. Blog public

- [ ] `/blog` 200 + 1× `og:title` + canonical
- [ ] `/blog?q=…` 200
- [ ] `/api/blog/latest` JSON
- [ ] Home `#blog` cards
- [ ] CSP: youtube/vk/rutube + `media-src https:`

## D. Blog admin B4

- [ ] `/admin/blog` список
- [ ] `/admin/blog/<slug>` деталка
- [ ] Invalidate cache работает
- [ ] Write OFF by default
- [ ] Write ON (optional GO): SEO/tags/excerpt сохраняются в Sheets; `final_posts` не editable в UI

## E. Camp HOLD

- [ ] Cron `/etc/cron.d/mywave-camp-sync` commented
- [ ] Нет внезапного mass-import

## F. Editorial process

- [ ] Новые строки: ASCII slug, cover, tags — по `docs/BLOG_EDITORIAL_CHECKLIST.md`

---

## Критерий «S11 light DONE»

Все A–C зелёные; D read OK; E hold подтверждён. Write-on (D optional) — отдельно по GO.
