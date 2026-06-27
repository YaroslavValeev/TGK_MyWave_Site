#!/usr/bin/env bash
# Import main:app as service user — mandatory gate before/after .env changes.
set -euo pipefail

PROD_ROOT="${PROD_ROOT:-/var/www/mywave}"
RUN_USER="${RUN_USER:-$(systemctl show mywave-site -p User --value 2>/dev/null || echo www-data)}"
VENV_PY="${PROD_ROOT}/venv/bin/python"

if [[ ! -x "$VENV_PY" ]]; then
  echo "FAIL: venv python not found: ${VENV_PY}"
  exit 1
fi

echo "=== prod_import_as_run_user ==="
echo "run_user=${RUN_USER}"
echo "prod_root=${PROD_ROOT}"

sudo -u "$RUN_USER" bash -lc "cd '${PROD_ROOT}' && '${VENV_PY}' - <<'PY'
import os
os.environ.setdefault('ENABLE_GOOGLE_SERVICES', '0')
from main import app
print('IMPORT_OK_AS_RUN_USER')
print('app_name', app.name)
PY"

echo "IMPORT_CHECK=PASS"
