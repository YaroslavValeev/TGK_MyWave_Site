#!/usr/bin/env bash
# PR56 production smoke — read-only HTTP checks + assign gating.
# Usage:
#   bash automation/production/prod_pr56_smoke.sh           # Phase A (default)
#   bash automation/production/prod_pr56_smoke.sh --phase-b # Phase B (token checks)
set -euo pipefail

BASE="${MYWAVE_BASE_URL:-http://127.0.0.1:5000}"
BASE="${BASE%/}"
PHASE="${1:-}"
FAIL=0
DATE="${SMOKE_SLOT_DATE:-$(date +%F)}"

_check() {
  local name="$1" url="$2" expect="$3"
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 "$url" || echo "000")"
  if [[ "$code" == "$expect" ]] || [[ "$expect" == *"$code"* ]]; then
    echo "OK   $name  $code"
  else
    echo "FAIL $name  $code (expected $expect)"
    FAIL=1
  fi
}

echo "=== PR56 smoke ==="
echo "base=${BASE} phase=${PHASE:-A}"

_check "health_live" "${BASE}/health/live" "200"
_check "health_ready" "${BASE}/health/ready" "200"
_check "home" "${BASE}/" "200"
_check "social" "${BASE}/social" "200"
_check "slots_boat" "${BASE}/api/calendar/slots/${DATE}?service=boat" "200"

# Phase A: assign must be 503 when SOCIAL_BOOKING_ENABLED=false
ASSIGN_CODE="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 \
  -X POST "${BASE}/api/social/sessions/assign" \
  -H 'Content-Type: application/json' \
  -d '{"application_id":"soc_app_aabbccddeeff0011","session_date":"2026-07-01","session_time":"10:00","assigned_by":"smoke"}')"
if [[ "$PHASE" == "--phase-b" ]]; then
  if [[ "$ASSIGN_CODE" == "401" ]] || [[ "$ASSIGN_CODE" == "403" ]]; then
    echo "OK   assign_no_token  ${ASSIGN_CODE}"
  else
    echo "FAIL assign_no_token  ${ASSIGN_CODE} (expected 401/403)"
    FAIL=1
  fi
else
  if [[ "$ASSIGN_CODE" == "503" ]]; then
    echo "OK   assign_disabled  503"
  else
    echo "FAIL assign_disabled  ${ASSIGN_CODE} (expected 503)"
    FAIL=1
  fi
fi

# Public apply must not hit assign (regression marker — route exists but gated)
echo "public_apply_route=/api/social/apply (no assign side-effect — verified in unit tests)"

if [[ "$FAIL" -ne 0 ]]; then
  echo "PR56_SMOKE=FAIL"
  exit 1
fi
echo "PR56_SMOKE=PASS"
