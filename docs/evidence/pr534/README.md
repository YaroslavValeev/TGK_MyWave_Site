# PR53.4 — mobile QA follow-up

## Scope
1. Competitions carousel mobile autoplay (`MOBILE_AUTO_SCROLL = true`, 840s)
2. Footer link «Социальная ответственность» + mobile safe-area above chat
3. Telegram notification status sanitize (no MagicMock/object repr)

## Tests
```bash
pytest tests/unit/test_pr534_mobile_qa_followup.py \
       tests/unit/test_application_notifications.py \
       tests/unit/test_competitions_ticker.py -q
```

## Visual evidence (Owner QA after deploy)
- [ ] Mobile 360/390px: competitions ticker autoscroll (video/screenshot)
- [ ] Mobile footer: «Социальная ответственность» visible, link to `/social`
- [ ] Product lead Telegram: `Статус: new` (no MagicMock)

Deploy status: **NOT STARTED**
