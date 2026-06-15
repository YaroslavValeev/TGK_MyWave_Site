# Site — OpenAI EU SOCKS5 proxy readiness

**Status:** docs-only (GM accepted 2026-06-14)  
**Track:** Site infra / OpenAI proxy readiness  
**Priority:** P2  
**Production action:** **NOT APPROVED** until separate GM maintenance window  
**Related:** Events-3 staging QA — separate track, do not mix

---

## 1. Summary

Site **already calls OpenAI from the server** (Flask/Gunicorn on VPS). Requests go **server → OpenAI API**, not from the visitor's browser. A VPN on the owner's PC does **not** fix geo-block from a RU VPS.

Proxy support is **partially implemented** in code (`OPENAI_HTTP_PROXY` → `httpx.Client(proxy=...)`). For **SOCKS5**, the Python env must also have **`httpx[socks]`** / `socksio` (not in `requirements.txt` yet).

**Telethon is not used by Site.** Telegram integration uses **python-telegram-bot** (Bot API webhook). Bot API traffic typically does **not** need a SOCKS proxy for Site.

---

## 2. Site OpenAI live paths

| Path | Module / route | Function | Notes |
|------|----------------|----------|-------|
| Public chat | `app/routes/chat.py` | `POST /chat/api` → `ask()` | Primary prod consumer |
| Booking AI | `app/services/booking_orchestrator.py` | `respond_structured()` | Via chat booking flow |
| Telegram webhook | `app/routes/telegram/routes.py` | `ask()` | Only if `TELEGRAM_BOT_TOKEN` enabled |
| AI gateway | `app/ai/core_gateway.py` | `ask()` | Optional façade |
| Assistant admin | `scripts/create_assistant_from_prompt.py` | `create_assistant()` | Dev/ops script only |

**Central factory (proxy-aware):**

```text
app/services/openai_service.py
  _openai_client_from_config()
    → reads OPENAI_HTTP_PROXY | HTTPS_PROXY | HTTP_PROXY
    → httpx.Client(proxy=...)
    → OpenAI(api_key=..., http_client=...)
```

**Config load:**

```text
config.py → OPENAI_HTTP_PROXY = os.getenv("OPENAI_HTTP_PROXY") or HTTPS_PROXY or HTTP_PROXY
```

**Not live today:**

| Item | Evidence |
|------|----------|
| `rag_api` (`get_embedding_vector`) | Blueprint not registered in `app/__init__.py` |
| `voice_api` (`transcribe_audio`) | Blueprint not registered; symbols missing in `openai_service.py` |
| `ai_router._get_openai_client()` | **Defined only, never called** (see §8) |

---

## 3. `OPENAI_HTTP_PROXY` behavior

**Env var (staging/prod `.env` only — never commit):**

```text
OPENAI_HTTP_PROXY=socks5://USER:PASSWORD@EU_HOST:PORT
# or HTTP CONNECT:
OPENAI_HTTP_PROXY=http://USER:PASSWORD@EU_HOST:PORT
```

**Fallback order in code:** `OPENAI_HTTP_PROXY` → `HTTPS_PROXY` → `HTTP_PROXY`.

**On success:** log line (no secrets):

```text
[openai-client] using HTTP proxy for API requests
```

**On proxy init failure:** warning + direct connection attempt (may hit region block).

**After `.env` change:** restart **only** the target service (`mywave-staging` or `mywave-site`).

Documented in repo: `.env.example` (placeholders only).

---

## 4. Dependencies

| Package | `requirements.txt` | Notes |
|---------|-------------------|-------|
| `openai` | `>=1.70.0,<2.0.0` | Official SDK; accepts custom `http_client` |
| `httpx` | `>=0.24.0` | Used for proxy transport |
| `httpx[socks]` / `socksio` | **missing** | **Required for `socks5://` URLs** |

**Staging smoke (when GM approves):**

```bash
cd /var/www/mywave-staging
source venv/bin/activate
pip install 'httpx[socks]'
# verify:
python -c "import socksio; import httpx; print('socks ok', httpx.__version__)"
```

**Production:** `pip install` + `requirements.txt` update only in GM maintenance window.

---

## 5. SOCKS users — project isolation (GM rule)

**Do not reuse Parser News SOCKS user for Site.**

| SOCKS user | Project | Host |
|------------|---------|------|
| `parser` | Parser News only | — |
| **`site_mywave`** | **Site / mywavewake.ru only** | — |
| `project2` | MyWaveTour or other | — |

Even if Parser and Site run on the **same RU VPS**, credentials must be **separate** per project:

- isolated access and audit;
- revoke one project without stopping others;
- no shared password in chat/issues/git.

**Wrong (do not use on Site):**

```text
OPENAI_HTTP_PROXY=socks5://parser:...@EU_HOST:1080   # Parser user — NOT for Site
```

**Correct (when `site_mywave` is issued via secure channel):**

```text
OPENAI_HTTP_PROXY=socks5://site_mywave:PASSWORD@EU_HOST:1080
```

Issue `site_mywave` password only via secure channel (not email, not GitHub, not this repo).

---

## 6. Staging-only smoke checklist (GM: later, conditional)

**Preconditions:**

- Events-3 evidence work not interrupted;
- `site_mywave` credentials issued securely;
- path: `/var/www/mywave-staging` only;
- restart: **`mywave-staging.service` only**;
- **no** `mywave-site`, bot, node, parser, prod `.env`.

**Steps:**

```bash
export STAGING_ROOT=/var/www/mywave-staging
cd "$STAGING_ROOT"
source venv/bin/activate

pip install 'httpx[socks]'

# Edit ONLY staging .env (placeholder — use real site_mywave creds offline):
# OPENAI_HTTP_PROXY=socks5://site_mywave:PASSWORD@EU_HOST:1080
# OPENAI_API_KEY=sk-...   (existing staging key)

sudo systemctl restart mywave-staging
sleep 3
sudo systemctl is-active mywave-staging

# Startup log (no secrets):
sudo journalctl -u mywave-staging -n 80 --no-pager | grep -E 'openai-chat-config|openai-client'

# Functional: open site chat, send one message via tunnel or nginx
# Expect: reply text, NOT "openai_region_blocked" / persistent 403 message
```

**Pass criteria:**

- `[openai-client] using HTTP proxy for API requests` in logs;
- chat returns a normal answer;
- no Traceback in `journalctl` for OpenAI path.

---

## 7. Production maintenance-window checklist (NOT APPROVED YET)

Do **not** execute until GM opens a dedicated window.

- [ ] GM sign-off on `site_mywave` SOCKS user live on EU gateway
- [ ] `httpx[socks]` added to `requirements.txt` and deployed to prod venv
- [ ] Backup prod `.env`: `cp .env .env.bak.$(date +%Y%m%d-%H%M%S)`
- [ ] Set `OPENAI_HTTP_PROXY=socks5://site_mywave:...@EU_HOST:PORT` in **`/var/www/mywave/.env` only**
- [ ] Confirm `CHAT_BACKEND=completions` (current prod policy)
- [ ] `sudo systemctl restart mywave-site` (not bot/node/parser)
- [ ] Smoke: `/health`, home, one chat message, booking chat path if enabled
- [ ] Monitor logs 15 min: no `openai_region_blocked`
- [ ] Document result in ops log / GM thread (no secrets)

**Explicitly not in scope for this window unless GM says otherwise:**

- merge to `main` for unrelated features;
- `mywave-telegram-bot` / Telethon proxy;
- Parser News `.env`.

---

## 8. Rollback

**Staging or production:**

```bash
# 1. Comment or remove OPENAI_HTTP_PROXY in .env
# 2. Restart only the service that was changed
sudo systemctl restart mywave-staging   # staging
# or
sudo systemctl restart mywave-site      # prod — GM window only

# 3. Restore .env from backup if needed
cp .env.bak.YYYYMMDD-HHMMSS .env
sudo systemctl restart <service>
```

**Effect:** OpenAI calls attempt direct connection again → likely geo-block on RU VPS; chat shows user-friendly error strings from `openai_service._user_friendly_openai_error()`.

---

## 9. Security rules

**Never commit or paste into git / issues / chat:**

- real `OPENAI_HTTP_PROXY` URLs with password;
- `PROXY_PASS`, `OPENAI_API_KEY`;
- service account JSON;
- Telegram bot tokens;
- raw EU gateway credentials.

**Repo may contain:** placeholders in `.env.example`, this runbook, audit summaries.

**If credentials were exposed:** rotate SOCKS password and OpenAI key; re-issue `site_mywave` on gateway.

---

## 10. `ai_router.py` gap — classification

**File:** `app/services/ai_router.py`  
**Symbol:** `_get_openai_client()` — creates `OpenAI(api_key=...)` **without** proxy.

**Evidence (Site codebase, 2026-06-14):**

```text
grep "_get_openai_client" → only definition in ai_router.py, zero call sites
```

**Live imports from `ai_router`:**

- `responses_api.py` → `get_user_chat_history`, `save_chat_message` only (Sheets helpers)
- tests mock `save_chat_message`

**Verdict:** `_get_openai_client()` is **dead code** — not on the live OpenAI path.

**Before production proxy window (code hygiene, optional small PR):**

1. Remove `_get_openai_client()` or replace body with delegate to `_openai_client_from_config()`; or
2. Add comment `# unused — use openai_service._openai_client_from_config` and delete in follow-up.

**No production change required** for proxy readiness if all OpenAI traffic stays on `openai_service.py` (current state).

---

## 11. Telegram / Telethon note

| Component | On Site? | Proxy needed? |
|-----------|----------|---------------|
| Telethon (MTProto user client) | **No** | N/A |
| python-telegram-bot (Bot API webhook) | Optional (`TELEGRAM_BOT_TOKEN`) | Usually **no** for `api.telegram.org` from RU VPS |
| OpenAI chat/booking | **Yes** | **Yes** (EU SOCKS) when server is in blocked region |

Infra letter items about **Telethon + SOCKS** apply to **other projects** (e.g. Parser), not Site Flask app.

---

## 12. GM verdict log

| Item | Status |
|------|--------|
| Audit | **Accepted** |
| Docs-only in `develop` | **Approved** |
| Staging smoke | **Conditionally approved later** |
| Production `.env` / restart | **Blocked** |
| Separate SOCKS user `site_mywave` | **Required** |
| Reuse `parser` SOCKS user on Site | **Forbidden** |

---

## 13. Related files

| File | Role |
|------|------|
| `app/services/openai_service.py` | Proxy-aware client factory |
| `config.py` | `OPENAI_HTTP_PROXY` in Flask config |
| `.env.example` | Placeholder documentation |
| `docs/CHAT_RUNTIME_AND_RELEASE.md` | Chat backend / release notes |
| `scripts/prod_deploy_site.sh` | Mentions `OPENAI_HTTP_PROXY` in env grep (prod ops) |
