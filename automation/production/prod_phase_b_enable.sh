#!/usr/bin/env bash
# PR56 Phase B — controlled enable (Owner-approved).
# HEAD must stay 716d81c0. Restart only mywave-site. No secrets printed.
#
# Usage:
#   cd /var/www/mywave
#   # optional: export SOCIAL_PHASE_B_APP_ID=soc_app_...
#   sudo bash automation/production/prod_phase_b_enable.sh
#
# Rollback safe mode only:
#   sudo bash automation/production/prod_phase_b_enable.sh --rollback-safe
set -euo pipefail

PROD_ROOT="${PROD_ROOT:-/var/www/mywave}"
ENV_FILE="${PROD_ROOT}/.env"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE="${MYWAVE_BASE_URL:-http://127.0.0.1:5000}"
BASE="${BASE%/}"
PHASE_B_APP_ID="${SOCIAL_PHASE_B_APP_ID:-}"

if [[ "${1:-}" == "--rollback-safe" ]]; then
  echo "=== PR56 Phase B rollback (safe mode only) ==="
  sed -i 's/^SOCIAL_BOOKING_ENABLED=.*/SOCIAL_BOOKING_ENABLED=false/' "$ENV_FILE"
  bash "${SCRIPT_DIR}/prod_env_permissions_fix.sh"
  bash "${SCRIPT_DIR}/prod_env_readable_check.sh"
  bash "${SCRIPT_DIR}/prod_import_as_run_user.sh"
  systemctl restart mywave-site
  sleep 3
  systemctl is-active mywave-site
  CODE="$(curl -sS -o /dev/null -w '%{http_code}' -X POST "${BASE}/api/social/sessions/assign" \
    -H 'Content-Type: application/json' \
    -d '{"application_id":"soc_app_rollback","session_date":"2026-07-01","session_time":"10:00","assigned_by":"rollback"}')"
  echo "assign_after_rollback=${CODE}"
  bash "${SCRIPT_DIR}/prod_pr56_smoke.sh"
  echo "ROLLBACK_SAFE=COMPLETE"
  exit 0
fi

echo "=== PR56 Phase B enable ==="
cd "$PROD_ROOT"

echo "--- A. Preflight ---"
HEAD="$(git rev-parse HEAD)"
echo "HEAD=${HEAD}"
[[ "$HEAD" == "716d81c0"* ]] || echo "WARN: unexpected HEAD (expected 716d81c0)"
systemctl is-active mywave-site
df -h / | tail -1
TS="$(date +%Y%m%d_%H%M%S)"
mkdir -p /var/backups/mywave
cp -a "$ENV_FILE" "/var/backups/mywave/.env.pre_phase_b_${TS}"
echo "backup=/var/backups/mywave/.env.pre_phase_b_${TS}"
bash "${SCRIPT_DIR}/prod_env_permissions_fix.sh"
bash "${SCRIPT_DIR}/prod_social_sessions_headers_check.sh"

echo "--- B. ADMIN_TOKEN setup ---"
if grep -qE '^ADMIN_TOKEN=.+' "$ENV_FILE" 2>/dev/null; then
  echo "ADMIN_TOKEN: already SET (skip regenerate)"
  bash "${SCRIPT_DIR}/prod_env_permissions_fix.sh"
  bash "${SCRIPT_DIR}/prod_env_readable_check.sh"
  bash "${SCRIPT_DIR}/prod_import_as_run_user.sh"
else
  bash "${SCRIPT_DIR}/prod_admin_token_setup.sh"
fi

echo "--- C. Enable SOCIAL_BOOKING_ENABLED=true ---"
bash "${SCRIPT_DIR}/prod_env_readable_check.sh" | grep -E 'ADMIN_TOKEN:|SOCIAL_BOOKING'
grep -q '^SOCIAL_BOOKING_ENABLED=' "$ENV_FILE" \
  && sed -i 's/^SOCIAL_BOOKING_ENABLED=.*/SOCIAL_BOOKING_ENABLED=true/' "$ENV_FILE" \
  || echo 'SOCIAL_BOOKING_ENABLED=true' >> "$ENV_FILE"
bash "${SCRIPT_DIR}/prod_env_permissions_fix.sh"
bash "${SCRIPT_DIR}/prod_env_readable_check.sh"
bash "${SCRIPT_DIR}/prod_import_as_run_user.sh"

echo "--- D. Restart mywave-site ---"
systemctl restart mywave-site
sleep 3
systemctl is-active mywave-site
curl -fsS "${BASE}/health/live" >/dev/null && echo "/health/live: ok"
curl -fsS "${BASE}/health/ready" >/dev/null && echo "/health/ready: ok"

echo "--- E. Security smoke ---"
PAYLOAD='{"application_id":"soc_app_smoke0000000000","session_date":"2026-07-15","session_time":"10:00","assigned_by":"phase_b_smoke"}'
curl -sS -o /dev/null -w 'no_token: %{http_code}\n' \
  -X POST "${BASE}/api/social/sessions/assign" \
  -H 'Content-Type: application/json' -d "$PAYLOAD"
curl -sS -o /dev/null -w 'bad_token: %{http_code}\n' \
  -X POST "${BASE}/api/social/sessions/assign" \
  -H 'Content-Type: application/json' \
  -H 'X-Admin-Token: invalid-token-phase-b' -d "$PAYLOAD"
bash "${SCRIPT_DIR}/prod_pr56_smoke.sh" --phase-b

echo "--- F. Assignable applications (id + status only) ---"
"${PROD_ROOT}/venv/bin/python" - <<'PY'
import os, sys
from pathlib import Path
PROD_ROOT = Path("/var/www/mywave")
sys.path.insert(0, str(PROD_ROOT)); os.chdir(PROD_ROOT)
import importlib.util
spec = importlib.util.spec_from_file_location("_pe", PROD_ROOT/"automation/production/_prod_env.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
mod.load_prod_dotenv(str(PROD_ROOT))
from app import create_app
from app.services.google_sheets_service import read_records
from app.services.social_store import resolve_social_sheet_name, resolve_social_spreadsheet_id
from app.services.social_schema import SOCIAL_APPLICATIONS_SHEET, ASSIGNABLE_APPLICATION_STATUSES, SOCIAL_SESSIONS_SHEET
app = create_app("production")
assignable = []
with app.app_context():
    sid = resolve_social_spreadsheet_id()
    apps = read_records(sid, resolve_social_sheet_name("SOCIAL_APPLICATIONS_SHEET_NAME", SOCIAL_APPLICATIONS_SHEET))
    sessions = read_records(sid, resolve_social_sheet_name("SOCIAL_SESSIONS_SHEET_NAME", SOCIAL_SESSIONS_SHEET))
    scheduled_apps = {
        str(s.get("application_id") or "").strip().lower()
        for s in sessions
        if str(s.get("status") or "").strip().lower() == "scheduled"
    }
    print("assignable_applications:")
    for r in apps:
        aid = str(r.get("application_id") or "").strip()
        st = str(r.get("status") or "").strip().lower()
        if not aid or st not in ASSIGNABLE_APPLICATION_STATUSES:
            continue
        if aid.lower() in scheduled_apps:
            print(f"  SKIP {aid} status={st} (session already scheduled)")
            continue
        print(f"  OK   {aid} status={st}")
        assignable.append(aid)
    if not assignable:
        print("FAIL: no assignable application without scheduled session")
        raise SystemExit(2)
    Path("/tmp/social_phase_b_first_assignable.txt").write_text(assignable[0], encoding="utf-8")
    print(f"default_candidate={assignable[0]}")
PY

APP_ID="${PHASE_B_APP_ID}"
if [[ -z "$APP_ID" ]]; then
  APP_ID="$(cat /tmp/social_phase_b_first_assignable.txt 2>/dev/null || true)"
fi
if [[ -z "$APP_ID" ]]; then
  echo "FAIL: set SOCIAL_PHASE_B_APP_ID or ensure assignable list non-empty"
  exit 2
fi
echo "controlled_assign_application_id=${APP_ID}"

echo "--- G. Controlled manual assign ---"
ADMIN_TOKEN="$(grep '^ADMIN_TOKEN=' "$ENV_FILE" | cut -d= -f2- | tr -d '\r\"')"
echo "ADMIN_TOKEN_LEN=${#ADMIN_TOKEN}"
RESP_FILE="/tmp/social_phase_b_assign_resp.json"
HTTP_CODE="$(curl -sS -o "$RESP_FILE" -w '%{http_code}' \
  -X POST "${BASE}/api/social/sessions/assign" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H 'Content-Type: application/json' \
  -d "{
    \"application_id\": \"${APP_ID}\",
    \"session_date\": \"2026-07-15\",
    \"session_time\": \"10:00\",
    \"assigned_by\": \"owner_phase_b_test\",
    \"location\": \"Павильон\",
    \"service_type\": \"adaptive_wake\",
    \"coach\": \"Phase B Test\",
    \"source\": \"manual_assign_phase_b\"
  }")"
echo "manual_assign_http=${HTTP_CODE}"
python3 - <<PY
import json
from pathlib import Path
p = Path("/tmp/social_phase_b_assign_resp.json")
if p.is_file():
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        safe = {k: d.get(k) for k in ("ok", "session_id", "application_id", "status", "error")}
        print("manual_assign_response:", json.dumps(safe, ensure_ascii=False))
    except Exception as e:
        print("manual_assign_response_raw_len", len(p.read_text(encoding="utf-8", errors="replace")))
PY

echo "--- H. Final smoke ---"
curl -fsS -o /dev/null -w '/social: %{http_code}\n' "${BASE}/social"
curl -fsS -o /dev/null -w '/slots: %{http_code}\n' "${BASE}/api/calendar/slots/$(date +%F)?service=boat"
bash "${SCRIPT_DIR}/prod_pr56_smoke.sh" --phase-b
bash "${SCRIPT_DIR}/prod_social_sessions_headers_check.sh"

echo "=== Phase B script complete ==="
echo "Verify in Sheets: Social_Sessions + 2x Social_Audit_Log rows"
echo "Verify Telegram: sanitized session scheduled (no health/PII)"
echo "journalctl hint: journalctl -u mywave-site -n 50 --no-pager | grep social_session"
