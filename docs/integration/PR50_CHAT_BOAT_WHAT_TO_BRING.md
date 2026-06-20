# PR50 — Chat KB: «Что взять на катер?»

**Status:** ready for GM review (not committed/deployed unless approved)  
**Follow-up to:** PR49 Owner QA — chat answer quality PARTIAL  
**Date:** 2026-06-19

## Problem

Browser QA after PR49:

- Question: «Что взять на катер?»
- Got disambiguation: «вам нужна запись в зал или на катер?»
- Expected: direct practical boat checklist

**Root cause:** `_needs_location_disambiguation()` fired before checking that «катер» is already in the user message.

## Solution (minimal)

1. `what_to_bring_location()` + `try_direct_what_to_bring_reply()` in `responses_api.py`
2. `chat.py`: direct checklist when location is explicit (boat/gym); disambiguation only for ambiguous questions
3. KB `WhatToBring_GymVsBoat.txt` aligned with canonical boat list
4. `_collect_knowledge_snippets`: keywords `катер` / `катере` → training KB

## Acceptance criteria

| Case | Expected |
|------|----------|
| «Что взять на катер?» | Direct boat checklist, no зал/катер question |
| «что взять с собой на катер» | Same |
| «Что нужно с собой взять?» (no location) | Still asks зал or катер |
| Booking intent | Unchanged (orchestrator) |

## Files (planned)

- `app/services/responses_api.py`
- `app/routes/chat.py`
- `knowledge_base/wakesurfing_tips.txt/WhatToBring_GymVsBoat.txt`
- `tests/integration/test_chat_api.py`
- `tests/unit/test_responses_api_knowledge.py`
- `docs/integration/PR50_CHAT_BOAT_WHAT_TO_BRING.md`

## Tests

```bash
pytest tests/unit/test_responses_api_knowledge.py tests/integration/test_chat_api.py -q -k "what_to_bring or boat_what"
```

## Out of scope

- `OPENAI_HTTP_PROXY` / `.env`
- Booking flow changes
- Full chat prompt rewrite

## Deploy

Separate from PR49; requires GM approval for commit → merge → prod fast-forward.
