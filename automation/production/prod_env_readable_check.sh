#!/usr/bin/env bash
# Verify .env is readable by mywave-site service user (mandatory before restart).
set -euo pipefail

PROD_ROOT="${PROD_ROOT:-/var/www/mywave}"
ENV_FILE="${ENV_FILE:-${PROD_ROOT}/.env}"
RUN_USER="${RUN_USER:-$(systemctl show mywave-site -p User --value 2>/dev/null || echo www-data)}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "FAIL: .env not found"
  exit 1
fi

echo "=== prod_env_readable_check ==="
echo "run_user=${RUN_USER}"
echo "env_file=${ENV_FILE}"

sudo -u "$RUN_USER" python3 - <<PY
from pathlib import Path
p = Path("${ENV_FILE}")
text = p.read_text(encoding="utf-8")
if not text.strip():
    raise SystemExit("FAIL: .env empty")
print("ENV_READABLE_BY_RUN_USER=YES")
print("env_line_count", len(text.splitlines()))
PY

# Redacted flag snapshot (no secret values)
sudo -u "$RUN_USER" python3 - <<'PY'
import re
from pathlib import Path

path = Path("/var/www/mywave/.env")
lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

def last(key):
    val = ""
    for ln in lines:
        if ln.strip().startswith("#"):
            continue
        m = re.match(rf"^{re.escape(key)}=(.*)$", ln.strip())
        if m:
            val = m.group(1).strip().strip('"').strip("'")
    return val

admin = last("ADMIN_TOKEN")
print("ADMIN_TOKEN:", "SET" if admin else "MISSING")
if admin:
    print("ADMIN_TOKEN_FP:", admin[:4] + "…" if len(admin) > 4 else "short")

booking = last("SOCIAL_BOOKING_ENABLED").lower()
if booking in ("1", "true", "yes", "on"):
    print("SOCIAL_BOOKING_ENABLED_VALUE: true")
else:
    print("SOCIAL_BOOKING_ENABLED_VALUE: false")
PY

echo "ENV_READABLE_CHECK=PASS"
