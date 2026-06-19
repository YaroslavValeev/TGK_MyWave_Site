# PR49 — Post-rollout hotfix package (Owner QA partial)

**Base:** `origin/main` @ PR #48 merge (`d1788685`)  
**Branch:** `hotfix/pr49-post-rollout-fixes`  
**Rollback PR48:** not required

## Defects addressed

| ID | Issue | Fix |
|----|-------|-----|
| A | Hero content too low / over busy background | CSS `translateY(-52px)` desktop, `-16px` ≤768px in `branding.css` |
| B | Checklist card media not full-width | Prefer `Check1.png` cover + `object-fit: cover` on checklist card |
| C | Chat unavailable message | Investigation doc + KB fallback when region-block UX text returned |

## Files changed (expected)

- `static/css/branding.css`
- `templates/base.html` (cache bust `hero-logo10`)
- `app/services/showcases.py`
- `static/css/services-carousel.css`
- `app/services/responses_api.py`
- `tests/unit/test_home_hero_logo.py`
- `tests/unit/test_showcases.py`
- `tests/unit/test_responses_api_knowledge.py`
- `docs/integration/PR49_CHAT_INVESTIGATION.md`
- `docs/integration/PR49_HOTFIX_PACKAGE.md`

## Tests

```bash
pytest tests/unit/test_home_hero_logo.py tests/unit/test_showcases.py tests/unit/test_responses_api_knowledge.py -q
```

## Owner acceptance (after deploy)

- Desktop hero: logo/subtitle/CTA higher; subtitle off boat line
- Mobile hero: logo not clipped; CTA visible
- Projects: checklist card media matches neighbors
- Chat: info question returns KB or GPT (see PR49_CHAT_INVESTIGATION.md)

## Deploy note

- `workflow_dispatch` deploy only with GM approval
- Restart: `mywave-site` after code deploy
- `OPENAI_HTTP_PROXY` change: separate GM step if logs confirm region block

## Evidence template (fill after deploy)

```
Commit: <sha>
Hero desktop screenshot: <attach>
Hero mobile screenshot: <attach>
Checklist card screenshot: <attach>
Chat POST /chat/api: <status> <response excerpt>
Logs clean: yes/no
Services restarted: mywave-site
Production touched: yes/no
Rollback needed: no (unless regression)
```
