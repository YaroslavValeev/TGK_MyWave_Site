#!/usr/bin/env bash
# Ensure blog media upload directories exist and are writable by www-data.
# Run on server as root after deploy or when POST /api/blog/media/upload returns 507.
set -euo pipefail

APP_ROOT="${APP_ROOT:-/var/www/mywave}"
SUBDIR="${MEDIA_UPLOAD_SUBDIR:-uploads/review_media}"
UPLOAD_DIR="${APP_ROOT}/static/${SUBDIR}"
LEGACY_DIR="${APP_ROOT}/static/downloads"
OWNER="${APP_OWNER:-www-data}"

mkdir -p "$UPLOAD_DIR" "$LEGACY_DIR"
chown -R "${OWNER}:${OWNER}" "${APP_ROOT}/static/uploads" "$LEGACY_DIR"
chmod 775 "$UPLOAD_DIR" "$LEGACY_DIR"

if sudo -u "$OWNER" test -w "$UPLOAD_DIR"; then
  echo "OK: ${UPLOAD_DIR} writable by ${OWNER}"
else
  echo "FAIL: ${UPLOAD_DIR} not writable by ${OWNER}" >&2
  exit 1
fi
