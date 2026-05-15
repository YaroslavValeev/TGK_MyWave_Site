# Release: frontend — mobile-home.css v3 (pending on production)

| Field | Value |
|-------|-------|
| Date | 2026-05-15 |
| Release type | **frontend** |
| Target commit | `main` (≥ `48dc9c64`, includes `?v=3` in base.html) |
| Runtime | `3de56f8c` unchanged |
| Status | **PENDING DEPLOY** |

## Summary

Automated precheck (`000a7100`) found production HTML still references `mobile-home.css?v=2`. Repository canon uses `?v=3`. Device Mobile QA blocked until this frontend release is applied.

## Deploy steps

```bash
cd /var/www/mywave
git fetch origin && git pull --ff-only origin main
grep mobile-home templates/base.html
sudo systemctl restart mywave-site
curl -sS https://mywavewake.ru/ | grep mobile-home
bash scripts/qa_mobile_precheck.sh
bash scripts/production_smoke.sh
```

## Post-deploy (mandatory)

- [ ] PRODUCTION_AUDIT_LOG row  
- [ ] Update this release note with commit + PASS  
- [ ] Proceed to manual Mobile QA (Phase 1 Step 1)  

## Rollback

Revert to previous commit; `systemctl reload mywave-site`. Runtime baseline remains `3de56f8c`.
