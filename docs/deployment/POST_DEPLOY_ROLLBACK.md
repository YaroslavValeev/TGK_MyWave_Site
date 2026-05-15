# Post-deploy rollback (MyWaveWake)

## Known-good release

| Commit | Назначение |
|--------|------------|
| `68b46537` | Timeweb production release baseline |
| `3de56f8c` | **Frozen runtime** — откат backend |
| `48dc9c64` | Frontend/docs — mobile v3, smoke, runbooks |
| `0a2a0e1a` | QA/Ops governance — matrix, incident policy, release gate |
| `94fbc211` | Production state / canonical governance |

Индекс: [PRODUCTION_GOVERNANCE.md](../PRODUCTION_GOVERNANCE.md).  
После каждого prod deploy обновляйте PREV в [RELEASE_GATE_CHECKLIST.md](RELEASE_GATE_CHECKLIST.md).

## Rollback (2–5 минут)

```bash
cd /var/www/mywave
PREV=<previous_release_commit>
sudo systemctl stop mywave-site mywave-node mywave-telegram-bot
git fetch origin
git checkout "$PREV"
/var/www/mywave/venv/bin/pip install -r requirements.txt
sudo systemctl daemon-reload
sudo nginx -t && sudo systemctl reload nginx
sudo systemctl start mywave-site mywave-node mywave-telegram-bot
curl -fsS https://mywavewake.ru/health
curl -fsS -o /dev/null -w "%{http_code}\n" https://mywavewake.ru/blog
```

## Восстановление из backup

```bash
sudo tar -xzf /var/backups/mywave/mywave-backup-YYYYMMDD-HHMMSS.tar.gz -C /var/www/mywave
sudo chown -R www-data:www-data /var/www/mywave
sudo systemctl restart mywave-site mywave-node mywave-telegram-bot
```

Backup script: `deploy/scripts/backup_mywave.sh`
