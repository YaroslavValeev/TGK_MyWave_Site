# Release S2 — Online Coaching mobile polish

**Status:** ready for PR / Owner GO  
**Release SHA:** `01205a0b23f4be84aa8e03342c0018acb59ec8ce`  
**Base / rollback SHA:** `48700c5a9ce5f5979862c13a4a4b728bff2d7be7`  
**Branch:** `release/s2-oc-mobile-polish`  
**PR:** https://github.com/YaroslavValeev/TGK_MyWave_Site/pull/101  
**Scope:** OC mobile UX + RU statuses. No YClients, Camp, Blog, Parser, `.env`.

## Changes

1. Mobile cards for «Что входит в каждый формат» (desktop table kept).
2. Chat-safe bottom padding so floating chat does not cover CTA/cards.
3. Removed duplicate sections (`Кому подходит`, `Цены`).
4. Canonical RU status labels via `status_display_name()` in admin list/detail:
   - `waiting_payment` → Ожидает оплату
   - `video_received` → Видео получено
   - `in_review` → На разборе
   - `completed` → Завершено
5. FAQ does not promote WhatsApp/MAX (runtime form fields unchanged).

## Tests

```bash
pytest tests/unit/test_online_coaching_schema.py tests/unit/test_online_coaching_public_copy.py -q
```
