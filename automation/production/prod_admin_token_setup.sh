#!/usr/bin/env bash
# Safe ADMIN_TOKEN setup for PR56 manual assign prep.
# - Backs up .env
# - Generates token (not printed)
# - Keeps SOCIAL_BOOKING_ENABLED=false
# - Enforces root:www-data 640 on .env
# - Pre-restart checks + mywave-site restart + smoke
set -euo pipefail

PROD_ROOT="${PROD_ROOT:-/var/www/mywave}"
ENV_FILE="${PROD_ROOT}/.env"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "FAIL: ${ENV_FILE} not found"
  exit 1
fi

TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="/var/backups/mywave"
sudo mkdir -p "$BACKUP_DIR"
BACKUP="${BACKUP_DIR}/.env.pre_admin_token_${TS}"
sudo cp -a "$ENV_FILE" "$BACKUP"
echo "backup=${BACKUP}"

NEW_TOKEN="$(openssl rand -hex 32)"

# Write ADMIN_TOKEN without printing value
sudo python3 - <<PY
import re
from pathlib import Path

path = Path("${ENV_FILE}")
lines = path.read_text(encoding="utf-8").splitlines()
token = "${NEW_TOKEN}"
out = []
found = False
for ln in lines:
    if re.match(r"^ADMIN_TOKEN=", ln.strip()):
        out.append(f"ADMIN_TOKEN={token}")
        found = True
    else:
        out.append(ln)
if not found:
    out.append(f"ADMIN_TOKEN={token}")
path.write_text("\n".join(out) + "\n", encoding="utf-8")
PY

# Ensure SOCIAL_BOOKING stays OFF
if grep -q '^SOCIAL_BOOKING_ENABLED=' "$ENV_FILE"; then
  sudo sed -i 's/^SOCIAL_BOOKING_ENABLED=.*/SOCIAL_BOOKING_ENABLED=false/' "$ENV_FILE"
else
  echo 'SOCIAL_BOOKING_ENABLED=false' | sudo tee -a "$ENV_FILE" >/dev/null
fi

echo "ADMIN_TOKEN: SET"
echo "ADMIN_TOKEN_FP: ${NEW_TOKEN:0:4}…"
echo "SOCIAL_BOOKING_ENABLED_VALUE: false"

sudo bash "${SCRIPT_DIR}/prod_env_permissions_fix.sh"
sudo bash "${SCRIPT_DIR}/prod_env_readable_check.sh"
sudo bash "${SCRIPT_DIR}/prod_import_as_run_user.sh"

echo "=== restart mywave-site ==="
sudo systemctl restart mywave-site
sleep 3
sudo systemctl is-active mywave-site

echo "=== health ==="
curl -fsS http://127.0.0.1:5000/health/live >/dev/null && echo "/health/live: ok"
curl -fsS http://127.0.0.1:5000/health/ready >/dev/null && echo "/health/ready: ok"

echo "=== assign closed while SOCIAL_BOOKING_ENABLED=false ==="
CODE="$(curl -sS -o /dev/null -w '%{http_code}' \
  -X POST http://127.0.0.1:5000/api/social/sessions/assign \
  -H 'Content-Type: application/json' \
  -d '{"application_id":"soc_app_aabbccddeeff0011","session_date":"2026-07-01","session_time":"10:00","assigned_by":"setup_check"}')"
echo "assign_status_code=${CODE}"
if [[ "$CODE" != "503" ]]; then
  echo "WARN: expected 503 while SOCIAL_BOOKING_ENABLED=false, got ${CODE}"
fi

echo "ADMIN_TOKEN_SETUP=COMPLETE"
