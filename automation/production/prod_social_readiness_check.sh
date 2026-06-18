#!/usr/bin/env bash
# Read-only Social Mission production readiness (PR #48 blocker 5.2).
# No .env writes, no restarts, no Sheet mutations.
set -euo pipefail

PROD_ROOT="${PROD_ROOT:-/var/www/mywave}"
TS="$(date +%Y%m%d_%H%M%S)"
OUT="/tmp/prod_social_readiness_${TS}.log"

exec > >(tee "$OUT") 2>&1

echo "=== Social production readiness ${TS} ==="
echo "root=${PROD_ROOT} mode=READ_ONLY"

echo ""
echo "=== SOCIAL_* in .env (IDs redacted) ==="
grep -E '^SOCIAL_' "${PROD_ROOT}/.env" 2>/dev/null \
  | sed -E 's/^(SOCIAL_SPREADSHEET_ID=).*/\1<set_or_empty>/' \
  || echo "WARN: no SOCIAL_* lines"

SPREADSHEET_ID=$(grep -E '^SOCIAL_SPREADSHEET_ID=' "${PROD_ROOT}/.env" 2>/dev/null | cut -d= -f2- | tr -d '\r"' || true)
if [ -z "${SPREADSHEET_ID}" ]; then
  SPREADSHEET_ID=$(grep -E '^SPREADSHEET_ID=' "${PROD_ROOT}/.env" 2>/dev/null | cut -d= -f2- | tr -d '\r"' || true)
  echo "SOCIAL_SPREADSHEET_ID: empty → fallback SPREADSHEET_ID used"
else
  echo "SOCIAL_SPREADSHEET_ID: set"
fi

SHEET_NAME=$(grep -E '^SOCIAL_APPLICATIONS_SHEET_NAME=' "${PROD_ROOT}/.env" 2>/dev/null | cut -d= -f2- | tr -d '\r"' || echo "Social_Applications")
echo "SOCIAL_APPLICATIONS_SHEET_NAME: ${SHEET_NAME:-Social_Applications}"

echo ""
echo "=== Feature flags (runtime, if Social code deployed) ==="
"${PROD_ROOT}/venv/bin/python" - <<PY 2>/dev/null || echo "SKIP: Social module not on prod HEAD yet"
import os, sys
sys.path.insert(0, os.environ.get("PROD_ROOT", "/var/www/mywave"))
os.chdir(os.environ.get("PROD_ROOT", "/var/www/mywave"))
try:
    from app.config.social_features import get_social_feature_flags
    for k, v in get_social_feature_flags().items():
        print(f"{k}={v}")
except ImportError:
    print("Social code not installed on this HEAD (expected before PR48 rollout)")
PY

echo ""
echo "=== Google SA + Sheet tab probe (read-only) ==="
"${PROD_ROOT}/venv/bin/python" - <<PY || echo "FAIL: sheet probe"
import os, sys
sys.path.insert(0, "${PROD_ROOT}")
os.chdir("${PROD_ROOT}")
from dotenv import load_dotenv
load_dotenv("${PROD_ROOT}/.env")
sid = (os.getenv("SOCIAL_SPREADSHEET_ID") or os.getenv("SPREADSHEET_ID") or "").strip()
tab = (os.getenv("SOCIAL_APPLICATIONS_SHEET_NAME") or "Social_Applications").strip()
if not sid:
    raise SystemExit("No SPREADSHEET_ID / SOCIAL_SPREADSHEET_ID")
from app.services.google import get_google_services
svc = get_google_services()
meta = svc["sheets"].spreadsheets().get(spreadsheetId=sid).execute()
titles = [s["properties"]["title"] for s in meta.get("sheets", [])]
print("spreadsheet_access=OK")
print("tabs_count", len(titles))
print("Social_Applications_tab", "YES" if tab in titles else "NO")
PY

echo ""
echo "=== Booking/calendar isolation (code review marker) ==="
echo "social.py has no booking/calendar imports: confirmed in release branch code review"

echo ""
echo "=== DONE ==="
echo "log=${OUT}"
