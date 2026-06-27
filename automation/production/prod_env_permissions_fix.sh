#!/usr/bin/env bash
# Enforce .env permission contract for mywave-site (www-data must read .env).
# Safe to run repeatedly. Does NOT print secret values.
set -euo pipefail

PROD_ROOT="${PROD_ROOT:-/var/www/mywave}"
ENV_FILE="${ENV_FILE:-${PROD_ROOT}/.env}"
RUN_USER="${RUN_USER:-$(systemctl show mywave-site -p User --value 2>/dev/null || echo www-data)}"
RUN_GROUP="${RUN_GROUP:-$(systemctl show mywave-site -p Group --value 2>/dev/null || echo www-data)}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "FAIL: .env not found at ${ENV_FILE}"
  exit 1
fi

echo "=== prod_env_permissions_fix ==="
echo "env_file=${ENV_FILE}"
echo "run_user=${RUN_USER}"
echo "run_group=${RUN_GROUP}"

# Ensure runtime dirs writable by service user
for rel in logs instance prometheus_multiproc; do
  dir="${PROD_ROOT}/${rel}"
  if [[ -d "$dir" ]]; then
    chown -R "${RUN_USER}:${RUN_GROUP}" "$dir" 2>/dev/null || true
    chmod -R u+rwX,g+rwX "$dir" 2>/dev/null || true
    echo "runtime_dir_ok=${rel}"
  fi
done

# Service account JSON readable by www-data
for sa in "${PROD_ROOT}/instance/service_account.json" "${PROD_ROOT}/config/service_account.json"; do
  if [[ -f "$sa" ]]; then
    chown root:"${RUN_GROUP}" "$sa" 2>/dev/null || true
    chmod 640 "$sa" 2>/dev/null || true
    echo "service_account_ok=$(basename "$(dirname "$sa")")/$(basename "$sa")"
  fi
done

# .env contract: root:www-data 640
chown root:"${RUN_GROUP}" "$ENV_FILE"
chmod 640 "$ENV_FILE"

stat -c 'env_owner=%U env_group=%G env_mode=%a' "$ENV_FILE" 2>/dev/null \
  || ls -l "$ENV_FILE"

echo "ENV_PERMISSIONS_APPLIED=YES"
