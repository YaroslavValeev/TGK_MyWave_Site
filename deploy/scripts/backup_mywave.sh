#!/usr/bin/env bash
# Ежедневный backup: проект, .env, SQLite и конфиги. Запуск: cron 0 3 * * *
# Переменные: MYWAVE_ROOT=/var/www/mywave, BACKUP_ROOT=/var/backups/mywave, BACKUP_KEEP_DAYS=7
set -euo pipefail

ROOT="${MYWAVE_ROOT:-/var/www/mywave}"
DEST="${BACKUP_ROOT:-/var/backups/mywave}/$(date +%Y%m%d-%H%M)"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-7}"
mkdir -p "$DEST"

if [[ -d "$ROOT" ]]; then
  cp -a "$ROOT" "$DEST/project" 2>/dev/null || true
  [[ -f "$ROOT/.env" ]] && cp -a "$ROOT/.env" "$DEST/.env.backup" || true
  find "$ROOT" -maxdepth 3 \( -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" \) -exec cp -a {} "$DEST/" \; 2>/dev/null || true
  for candidate in \
    "$ROOT/instance/service_account.json" \
    "$ROOT/configs/service_account.json" \
    "$ROOT/config/service_account.json"
  do
    if [[ -f "$candidate" ]]; then
      cp -a "$candidate" "$DEST/$(basename "$(dirname "$candidate")")_service_account.json.backup"
    fi
  done
fi

find "${BACKUP_ROOT:-/var/backups/mywave}" -mindepth 1 -maxdepth 1 -type d -mtime +"$KEEP_DAYS" -exec rm -rf {} + 2>/dev/null || true

echo "Backup: $DEST"
