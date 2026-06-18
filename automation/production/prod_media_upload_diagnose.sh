#!/usr/bin/env bash
# Read-only prod diagnostics for blog media upload 500/507.
# No restarts, no .env writes. Optional: run ensure_media_upload_dirs.sh to fix perms.
set -euo pipefail

PROD_ROOT="${PROD_ROOT:-/var/www/mywave}"
PROD_URL="${PROD_URL:-https://mywavewake.ru}"
SUBDIR="${MEDIA_UPLOAD_SUBDIR:-uploads/review_media}"
UPLOAD_DIR="${PROD_ROOT}/static/${SUBDIR}"
TS="$(date +%Y%m%d_%H%M%S)"
OUT="/tmp/prod_media_upload_diag_${TS}.log"

exec > >(tee "$OUT") 2>&1

echo "=== media upload diagnose ${TS} ==="
echo "root=${PROD_ROOT} url=${PROD_URL}"
echo "upload_dir=${UPLOAD_DIR}"
echo "mode=READ_ONLY"

echo ""
echo "=== MEDIA_UPLOAD_* (.env, token redacted) ==="
grep -E '^MEDIA_UPLOAD_' "${PROD_ROOT}/.env" 2>/dev/null \
  | sed -E 's/^(MEDIA_UPLOAD_TOKEN=).*/\1<redacted>/' \
  || echo "WARN: no MEDIA_UPLOAD_* in .env"

echo ""
echo "=== static_folder resolve (python) ==="
"${PROD_ROOT}/venv/bin/python" - <<'PY'
import os, sys
sys.path.insert(0, os.environ.get("PROD_ROOT", "/var/www/mywave"))
os.chdir(os.environ.get("PROD_ROOT", "/var/www/mywave"))
from main import app
with app.app_context():
    from app.routes.api import _resolve_media_upload_dir, _resolve_media_upload_root
    print("MEDIA_UPLOAD_ROOT", app.config.get("MEDIA_UPLOAD_ROOT") or "(default static_folder)")
    print("static_folder", app.static_folder)
    print("upload_root", _resolve_media_upload_root())
    print("upload_dir", _resolve_media_upload_dir())
PY

echo ""
echo "=== directory listing ==="
ls -la "${PROD_ROOT}/static" 2>&1 | head -20 || true
ls -la "${PROD_ROOT}/static/uploads" 2>&1 || echo "MISSING: static/uploads"
ls -la "$UPLOAD_DIR" 2>&1 || echo "MISSING: ${UPLOAD_DIR}"

echo ""
echo "=== www-data write probe ==="
if sudo -u www-data test -w "$UPLOAD_DIR" 2>/dev/null; then
  echo "writable=YES"
else
  echo "writable=NO  → run: sudo bash ${PROD_ROOT}/scripts/ensure_media_upload_dirs.sh"
fi

echo ""
echo "=== smoke (no file → expect 400 if token OK) ==="
if TOKEN_LINE=$(grep -E '^MEDIA_UPLOAD_TOKEN=' "${PROD_ROOT}/.env" 2>/dev/null); then
  TOKEN="${TOKEN_LINE#MEDIA_UPLOAD_TOKEN=}"
  code=$(curl -sS -o /dev/null -w '%{http_code}' -X POST \
    "${PROD_URL}/api/blog/media/upload" \
    -H "Authorization: Bearer ${TOKEN}" 2>/dev/null || echo "000")
  echo "POST /api/blog/media/upload (no file) http=${code}"
  code2=$(curl -sS -o /dev/null -w '%{http_code}' -X POST \
    "${PROD_URL}/api/blog/cache/invalidate" \
    -H "Authorization: Bearer ${TOKEN}" 2>/dev/null || echo "000")
  echo "POST /api/blog/cache/invalidate http=${code2}"
else
  echo "SKIP: MEDIA_UPLOAD_TOKEN not in .env"
fi

echo ""
echo "=== journalctl (media upload / unhandled, last 4h) ==="
journalctl -u mywave-site --since "4 hours ago" --no-pager \
  | grep -iE 'media_upload_|review_media|Unhandled exception|PermissionError|upload_dir' \
  | tail -30 || echo "none"

echo ""
echo "=== app.log tail (if present) ==="
tail -40 "${PROD_ROOT}/logs/app.log" 2>/dev/null \
  | grep -iE 'media_upload|PermissionError|review_media' || echo "none or no app.log"

echo ""
echo "=== DONE ==="
echo "log=${OUT}"
