# MyWave Online Coaching — Closure Report (PR83 / PR88 / PR86)

**Production HEAD (2026-07-07):** `e57538e5c6030979a5ee32f225d0f681d60e4af8`  
**Status:** DEPLOYED / E2E GREEN / ADMIN GREEN

---

## Delivered (production)

| PR | Scope | Status |
|----|--------|--------|
| **#83** | Video-step, `POST .../media`, Telegram video URLs, admin materials | DEPLOYED / E2E GREEN |
| **#88** | CSRF on admin POST forms (quick actions) | DEPLOYED / BROWSER GREEN |
| **#86** | Logger fallback if `logs/app.log` not writable | DEPLOYED / SERVER GREEN |
| **#87** | Online Coaching service card CTA on desktop | In `main` (with PR86 merge path) |

---

## Client flow (video check)

```
анкета → waiting_video → video-step → video_received
→ Telegram «Новые материалы» (URL + кнопки)
→ admin quick actions (POST)
```

---

## Admin quick actions (POST only)

| Кнопка | Статус |
|--------|--------|
| Запросить видео | `waiting_video` |
| Взять в работу | `in_review` |
| Разбор отправлен | `review_sent` |
| Ожидает оплату | `waiting_payment` |
| Оплачено | `paid` |
| Завершить | `completed` |
| Отменить тестовую заявку | `cancelled` |

GET `/quick-action` → **405** (no status mutation via URL).

---

## Tests (unit)

```bash
pytest tests/unit/test_online_coaching_*.py tests/unit/test_logger.py -q
# Expected: 50+ passed (OC suite + logger + admin CSRF/quick actions)
```

---

## Production deploy (mywave-site only)

```bash
cd /var/www/mywave
git pull --ff-only origin main
# verify: e57538e5...
sudo chown -R www-data:www-data logs instance
sudo systemctl restart mywave-site
sleep 12
curl -sf https://mywavewake.ru/health/live
```

**Do not touch:** `mywave-node`, TGbotAdmin, `mywave-telegram-bot`.

---

## Owner ops — test request cleanup

For E2E/test rows (`oc_req_*`):

1. Admin → Online Coaching → detail
2. **«Отменить тестовую заявку»** (quick action)
3. Or set status `cancelled` via dropdown

---

## Backlog (separate PRs — not part of OC closure)

- Browser QA home ticker / boat logos (PR80 lineage) — visual sign-off
- Phase 2: Telegram video file upload, T-Bank API/webhook, reminders cron
- WhatsApp/MAX automation

---

## Incident notes (resolved)

| Issue | Fix |
|-------|-----|
| Telegram «ссылка есть» without URL | PR83 materials notify + legacy URL patch |
| 502 after deploy | `logs/app.log` owned by root → chown www-data; PR86 hardening |
| CSRF on quick actions | PR88 csrf_token in forms |
