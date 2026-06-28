# PR56 — Rollback and safe mode

**Status:** reference (post-release)  
**Production baseline:** `3b70a038`  
**No deploy required** to merge docs/tests from PR68.

---

## Safe mode (preferred rollback)

Disable manual assign **without** code rollback. Keeps PR56 code and PR66 auth-fix on production.

| Action | Command (Owner, on prod) |
|--------|--------------------------|
| Disable assign | `SOCIAL_BOOKING_ENABLED=false` in `.env` |
| Fix permissions | `sudo bash automation/production/prod_env_permissions_fix.sh` |
| Pre-restart | `prod_env_readable_check.sh` + `prod_import_as_run_user.sh` |
| Restart | `sudo systemctl restart mywave-site` |
| Verify | `prod_pr56_smoke.sh` (Phase A → assign `503`) |

**Expected after safe mode:**

```text
POST /api/social/sessions/assign → 503 (social_booking_disabled)
GET  /health/live, /health/ready → 200
GET  /social → 200
Public /api/social/apply → unchanged (no assign)
```

Re-enable: set `SOCIAL_BOOKING_ENABLED=true`, repeat permissions + pre-restart gates, `prod_pr56_smoke.sh --phase-b`.

---

## Code rollback (boot failure only)

Use only if application fails to start after deploy. **Not** for assign logic bugs — use safe mode first.

```bash
cd /var/www/mywave
sudo -u www-data git reset --hard c35d19cc   # PR55 baseline
sudo bash automation/production/prod_env_permissions_fix.sh
sudo bash automation/production/prod_import_as_run_user.sh
sudo systemctl restart mywave-site
```

---

## Permission rollback (502 / gunicorn status=3)

**Try before code rollback** if site returns 502 after `.env` edit:

```bash
sudo bash automation/production/prod_env_permissions_fix.sh
sudo bash automation/production/prod_import_as_run_user.sh
sudo systemctl restart mywave-site
journalctl -u mywave-site -n 50 --no-pager
```

`.env` contract: `root:www-data`, mode `640`. Never `chmod 600`.

---

## What not to change without approval

```text
node, TGbotAdmin, Docker, apt, reboot
static/downloads/
SOCIAL_BOOKING_ENABLED / ADMIN_TOKEN (unless rollback approved)
```

---

## Related

- [PR56_PRODUCTION_ROLLOUT_RUNBOOK.md](PR56_PRODUCTION_ROLLOUT_RUNBOOK.md)
- [PR56_PRODUCTION_INCIDENT_20260627.md](../ops/PR56_PRODUCTION_INCIDENT_20260627.md)
- [docs/evidence/pr56/README.md](../evidence/pr56/README.md)
