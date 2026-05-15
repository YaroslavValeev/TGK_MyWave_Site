# Post-deploy rollback (MyWaveWake)

## Known-good release

- `68b465374c498cd55a8c1e48d33cf12f84000439` — Timeweb production release baseline

После post-deploy fixes зафиксируйте новый commit hash из `git rev-parse HEAD`.

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
