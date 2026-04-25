#!/usr/bin/env bash
# Ежедневный backup: проект, .env, SQLite. Запуск: cron 0 3 * * *
# Переменные: MYWAVE_ROOT=/var/www/mywave, BACKUP_ROOT=/var/backups/mywave
set -euo pipefail

ROOT="${MYWAVE_ROOT:-/var/www/mywave}"
DEST="${BACKUP_ROOT:-/var/backups/mywave}/$(date +%Y%m%d-%H%M)"
mkdir -p "$DEST"

if [[ -d "$ROOT" ]]; then
  cp -a "$ROOT" "$DEST/project" 2>/dev/null || true
  [[ -f "$ROOT/.env" ]] && cp -a "$ROOT/.env" "$DEST/.env.backup" || true
  find "$ROOT" -maxdepth 2 -name "*.db" -exec cp -a {} "$DEST/" \; 2>/dev/null || true
  [[ -f "$ROOT/configs/service_account.json" ]] && cp -a "$ROOT/configs/service_account.json" "$DEST/service_account.json.backup" || true
fi

echo "Backup: $DEST"
# retention: оставьте last N через отдельный find/rm по политике хоста
