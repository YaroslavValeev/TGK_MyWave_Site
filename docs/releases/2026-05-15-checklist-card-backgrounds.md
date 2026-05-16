# Release: checklist — card backgrounds (cardbg12)

**Date:** 2026-05-15  
**Type:** frontend (content page)  
**Production:** https://mywavewake.ru/projects/checklist-org  
**Commit:** `0b8972fa`

## Changes

- `data-checklist-asset-base` on `.wake-checklist` (paths without CSP-blocked inline script)
- Print inline script: `nonce="{{ csp_nonce }}"`
- Cache bust: `checklist.js` / `checklist.css` `?v=cardbg12`
- JS: image probe → `data-checklist-bg="ok"|"missing"`

## Deploy (server)

```bash
cd /var/www/mywave
git pull --ff-only origin main
ls static/images/Project/Cards/checklist/**/*.webp 2>/dev/null | wc -l   # expect 55
sudo systemctl restart mywave-site
curl -sS -o /dev/null -w '%{http_code}\n' https://mywavewake.ru/static/images/Project/Cards/checklist/app/app_event_information.webp
bash scripts/production_smoke.sh
```

## Verify (browser)

1. https://mywavewake.ru/projects/checklist-org — incognito, Ctrl+F5
2. DevTools: `.wake-checklist__card-art` + `data-checklist-bg="ok"`
3. Network → Img → webp **200**

## Rollback

Revert commit or set `?v=` back; `git pull` previous SHA + `systemctl restart mywave-site`.
