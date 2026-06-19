# PR49 — Chat «умный ассистент временно недоступен» (investigation)

**Status:** root cause identified (code path); prod log confirmation pending GM/Owner  
**Scope:** read-only diagnostics + minimal code fix for KB fallback gap  
**Date:** 2026-06-19

## 1. Symptom (Owner QA)

- Chat widget opens; socket/status may show online.
- Assistant reply: *«Сейчас умный ассистент временно недоступен с нашего сервера…»*
- Expected: GPT answer or offline KB answer for info questions.

## 2. Frontend endpoint (confirmed in repo)

| Item | Value |
|------|--------|
| File | `static/js/chat.js` |
| Method | `POST` |
| URL | `/chat/api` |
| Socket.IO | status only (`static/js/socket-status.js`), not chat transport |

Browser Network (Owner/GM on prod):

1. Open DevTools → Network → send a chat message.
2. Find `POST /chat/api` — note **status**, **response JSON** (`response`, `status`).
3. If 200 with unavailable text → backend/OpenAI path failed but handler returned UX message.

## 3. Backend path

```
POST /chat/api  →  app/routes/chat.py::chat_api()
  → ask() in app/services/openai_service.py
  → on PermissionDenied / region block:
       _user_friendly_openai_error() returns
       «Сейчас умный ассистент временно недоступен с нашего сервера…»
  → chat.py: if is_openai_failure_reply(reply) → try_offline_kb_reply(kb_snippets)
```

## 4. Root cause (code)

**Primary (prod infra):** OpenAI API **403 / region blocked** from RU-hosted server without outbound proxy.

- Message is generated in `openai_service.py` when `_is_region_blocked_error(exc)` is true.
- Mitigation on prod: set `OPENAI_HTTP_PROXY` (or `HTTPS_PROXY`) in `.env` to a proxy **outside RU**, restart `mywave-site` only (GM approval).

**Secondary (code bug, fixed in PR49):** `is_openai_failure_reply()` did **not** treat the user-facing region-block string as a failure, so **offline KB fallback did not run** even when snippets were collected.

- User saw the generic unavailable banner instead of KB text.
- PR49 adds marker: `умный ассистент временно недоступен`.

## 5. Prod read-only diagnostics (run on server)

```bash
# Site logs — chat / OpenAI / region
sudo journalctl -u mywave-site --since "2 hours ago" --no-pager \
  | grep -iE 'chat|openai|gpt|ai_gateway|socket|500|timeout|429|401|403|traceback|region_blocked' \
  | tail -120

# Node (status/socket only for site chat; still useful)
sudo journalctl -u mywave-node --since "2 hours ago" --no-pager \
  | grep -iE 'chat|openai|gpt|500|timeout|429|401|403|error' \
  | tail -120

# Config keys (names only — do not paste values)
cd /var/www/mywave
grep -E '^OPENAI_|^CHAT_|^GPTS_|^ASSISTANT_' .env | sed 's/=.*$/=***/'
```

**Expected log signature if region block:**

```
openai_region_blocked: настройте OPENAI_HTTP_PROXY в .env на сервере
```

## 6. Minimal fix plan

| Priority | Action | Owner | Restart |
|----------|--------|-------|---------|
| P0 (code) | Merge PR49: KB fallback on region-block user message | Site | `mywave-site` after deploy |
| P1 (prod env) | If logs show 403 region: set `OPENAI_HTTP_PROXY` | GM | `mywave-site` only |
| P2 (verify) | Retest: info question → KB or GPT; booking → orchestrator | Owner | — |

**Not in scope without GM:** secrets rotation, `mywave-node` restart, model changes.

## 7. Evidence checklist (post-deploy)

- [ ] `POST /chat/api` status + response body (screenshot or HAR snippet)
- [ ] `journalctl` lines with `openai_region_blocked` or absence thereof
- [ ] Chat test: «что взять на катер» → KB text (if proxy still off) or GPT (if proxy on)
- [ ] `/health` unchanged (ai_gateway optional)

## 8. Rollback

- Code: revert PR49 merge / redeploy previous HEAD.
- Env: restore `.env` from `/var/backups/mywave/.env.pre_ui_rollout_20260619_143237` if proxy trial fails.
