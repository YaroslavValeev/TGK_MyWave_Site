# PR70 — Admin UI MVP — Production Deploy Evidence

**Status:** DEPLOYED / SERVER-SIDE PASS — Browser QA **IN PROGRESS** (external access restored)  
**Date:** 2026-06-29  
**Merge commit:** `de37a19e` (`de37a19eccc2b9220acd4023e9d948cb315c759e`)  
**Production HEAD (after PR71):** `83daf51f`  
**Previous HEAD:** `3b70a038`  
**Production incident:** NO

## Deploy summary

| Check | Result |
|-------|--------|
| Code reset | `de37a19e` |
| `.env` backup | `/var/backups/mywave/.env.pre_pr70_20260629_091122` |
| `.env` permissions | `root:www-data` mode `640` |
| `ADMIN_TOKEN` | SET |
| `SOCIAL_BOOKING_ENABLED` | `true` |
| Import as `www-data` | PASS |
| `mywave-site` | active |
| `health/live` | ok |
| `health/ready` | ok |
| `prod_pr56_smoke.sh --phase-b` | PASS |
| `assign_no_token` | 401 |
| `assign_bad_token` | 401 |
| `/admin/social` (no session) | 302 (auth redirect) |
| `git_status` | `?? static/downloads/` only |

## Scope deployed

- `/admin/social` — list, detail, assign UI
- Uses existing `manual_assign_social_session`
- API `/api/social/sessions/assign` unchanged

## Not changed

- `.env` values (backup only)
- Feature flags
- PR56 API assign behavior

## Post-deploy (Owner)

- [x] Server-side deploy smoke — PASS (2026-06-29)
- [x] External access diagnostics — see below
- [ ] Browser QA: login admin → `/admin/social` — **IN PROGRESS** (VPN off; curl OK)

## External access diagnostics (2026-06-29)

| Layer | Result |
|-------|--------|
| Flask (`127.0.0.1:5000`) | health `200`, `/admin/social` `302` |
| Nginx config | `nginx -t` OK |
| Nginx local HTTPS | health `200`, `/admin/social` `302` |
| Public HTTPS from server (IPv4) | health `200` |
| DNS on server (`getent`) | `mywavewake.ru` → `62.113.42.227` |
| One `curl -6` or resolve variant | `Could not resolve host` (likely no AAAA) |
| Dev-machine external HTTP | timeout (client/network path) |

**Conclusion:** NOT a PR70 code incident. App + Nginx + public HTTPS from server are OK. Browser/dev timeout is **client-side network/DNS/IPv6 path** — not Flask regression.

Owner Browser QA: try `https://mywavewake.ru` and canonical `https://mywavetreaning.ru` once browser reaches site.

## Client-side diagnostics (Owner PC, 2026-06-29)

| Check | Result |
|-------|--------|
| DNS `mywavewake.ru` | resolves `62.113.42.227` (slow/untrusted DNS `10.255.255.1`) |
| `Test-NetConnection :443` | **TcpTestSucceeded** (via `wintun` VPN) |
| `curl -4 https://.../health/live` | **timeout** (TLS/HTTP layer) |
| `curl --resolve ...:443:62.113.42.227` | **timeout** (same) |
| Site team dev machine `curl -4` | **timeout** (reproduced) |
| SSH `5.129.249.113` | connection closed (**wrong IP** — prod DNS is `62.113.42.227`) |

**Pattern:** TCP:443 opens, HTTPS does not complete → **client VPN/path/MTU or edge filtering**, not PR70 Flask.

### Owner next steps (no server deploy)

1. **Disable VPN (`wintun`)** and retry browser + `curl -4 -I https://mywavewake.ru/health/live`
2. Try **mobile hotspot** or other network
3. If SSH to prod works: `ssh root@62.113.42.227` (not `5.129.249.113`)
4. Optional Browser QA tunnel (readonly): `ssh -L 8443:127.0.0.1:443 root@62.113.42.227` → browser `https://mywavewake.ru:8443/admin/social` (Host header via hosts file or curl only)
5. `openssl s_client -connect 62.113.42.227:443 -servername mywavewake.ru` — see if TLS handshake completes

Browser QA status: **IN PROGRESS** — VPN blocker **resolved** (2026-06-29); see `/login` blocker below.

### VPN resolved (Owner, 2026-06-29)

| Check | Result |
|-------|--------|
| VPN/wintun | **disabled** |
| `curl -4 https://mywavewake.ru/health/live` | **200** |
| `curl -4 https://mywavewake.ru/admin/social` | **308** → `/admin/social/` |

### Browser QA blocker: `/login` HTTP 500 (pre-existing, not PR70)

| Check | Result |
|-------|--------|
| `/admin/social/` (no auth) | 302 → `/login?next=...` |
| `GET /login` | **500** — `TemplateNotFound: auth/login.html` |
| Root cause | `auth.login` renders `auth/login.html`; template was missing (only `templates/login.html` for legacy `admin_panel.login`) |
| Fix | PR #71 — `templates/auth/login.html` (+ register) |
| Deploy | **DONE** (2026-06-29, see PR71 section) |

**Auth note for Browser QA:** `/admin/social` uses Flask-Login `User` DB (`email` + password, `is_admin=True`). Legacy `ADMIN_USERNAME`/`ADMIN_PASSWORD` env login (`admin_panel.login`) is a separate path.

## PR71 login hotfix deploy (2026-06-29)

**Merge commit:** `83daf51f` (`83daf51fc70710f10286fd8aabd83555375c1408`)  
**Previous HEAD:** `de37a19e`  
**Status:** DEPLOYED / SERVER-SIDE PASS

| Check | Result |
|-------|--------|
| Code reset | `83daf51f` |
| Import as `www-data` | PASS |
| `mywave-site` | active |
| `health/live`, `health/ready` | ok |
| `GET /login` (local + nginx public) | **200** |
| `/admin/social/` (no auth) | **302** → `/login?next=...` |
| `prod_pr56_smoke.sh --phase-b` | PASS |
| `.env` / feature flags | unchanged |
| `git_status` | `?? static/downloads/` only |

Browser QA status: **IN PROGRESS** — external access restored (VPN off, 2026-06-29).

### External access restored (Owner PC, VPN off, 2026-06-29)

| Check | Result |
|-------|--------|
| VPN/wintun | **disabled** |
| `https://mywavewake.ru/health/live` | **200** |
| `https://mywavewake.ru/login` | **200** |
| `https://mywavewake.ru/admin/social/` | **302** → `/login` |

**Conclusion:** blocker was VPN/client network path. PR70/PR71 code incident: **NO**. Nginx/Flask/prod: **OK**.

### Browser QA checklist (Owner, in progress)

1. Open `https://mywavewake.ru/admin/social/` → redirect to `/login` without session
2. Login: email user with `is_admin=True` (not legacy `ADMIN_USERNAME`)
3. List + filters
4. Detail — no `health_notes` / `motivation_text` / `internal_notes`
5. Assign form + confirmation screen
6. **No real assign** unless intentional

### Earlier client diagnostics (historical)

| Check | Result |
|-------|--------|
| With VPN / unstable path | intermittent `ERR_TIMED_OUT` |
| `curl /admin/social` (once) | **308** → `/admin/social/` |
| SSH tunnel `:8443` | failed (tunnel not listening locally) |

**Blocker type (resolved):** VPN/client network — not PR70/PR71 code.

## Rollback

Code: `git reset --hard 3b70a038` + permissions fix + restart (if needed).
