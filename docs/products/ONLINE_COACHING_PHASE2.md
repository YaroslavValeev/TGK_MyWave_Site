# MyWave Online Coaching — Phase 2

**Status:** implemented behind feature flags (default OFF)  
**Branch:** `feat/online-coaching-phase2`

## Scope

| Module | Flag | Description |
|--------|------|-------------|
| T-Bank API | `ONLINE_COACHING_TBANK_API_ENABLED` | Init payment + webhook → auto `mark_paid` |
| Reminders cron | `ONLINE_COACHING_REMINDERS_ENABLED` | `next_followup_at` → Telegram trainer notify |
| Telegram video | `ONLINE_COACHING_TELEGRAM_VIDEO_UPLOAD_ENABLED` | Webhook: video + caption `oc_req_*` |
| MAX / WhatsApp | `ONLINE_COACHING_CHANNEL_NOTIFY_ENABLED` | Outbound HTTP to client channel APIs |

Manual T-Bank URL flow (Phase 1) remains fallback.

## Env (see `env.example`)

```env
ONLINE_COACHING_TBANK_API_ENABLED=1
TBANK_TERMINAL_KEY=...
TBANK_SECRET_KEY=...
TBANK_NOTIFICATION_URL=https://mywavewake.ru/api/online-coaching/tbank/webhook

ONLINE_COACHING_REMINDERS_ENABLED=1

ONLINE_COACHING_TELEGRAM_VIDEO_UPLOAD_ENABLED=1
TELEGRAM_WEBHOOK_SECRET=...
# Webhook URL: POST /api/online-coaching/telegram/webhook

ONLINE_COACHING_CHANNEL_NOTIFY_ENABLED=1
MAX_API_URL=...
MAX_API_TOKEN=...
WHATSAPP_API_URL=...
WHATSAPP_API_TOKEN=...
```

## Cron (reminders)

```bash
# every hour
0 * * * * cd /var/www/mywave && DISABLE_TELEGRAM=0 ONLINE_COACHING_REMINDERS_ENABLED=1 \
  venv/bin/python scripts/run_online_coaching_reminders.py >> logs/oc_reminders.log 2>&1
```

Dry-run: `python scripts/run_online_coaching_reminders.py --dry-run`

## Telegram video upload

1. Client submits anketa → gets `online_request_id`
2. Sends video to notification bot with caption: `oc_req_xxxxxxxxxxxx`
3. Optional second line: review task text
4. Webhook ingests → `video_received` + trainer Telegram notify

## T-Bank flow

1. Admin → «Создать ссылку T-Bank (API)» (when configured)
2. Client pays → T-Bank POST webhook → `mark_paid` + Sales_Deals

## Do not touch

`mywave-node`, TGbotAdmin, `mywave-telegram-bot` — site-only webhooks.

## Tests

```bash
pytest tests/unit/test_online_coaching_phase2.py tests/unit/test_online_coaching_*.py -q
```
