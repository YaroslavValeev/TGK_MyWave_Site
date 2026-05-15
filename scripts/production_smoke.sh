#!/usr/bin/env bash
# Production smoke — read-only HTTP checks. Не меняет backend.
# Usage: MYWAVE_BASE_URL=https://mywavewake.ru bash scripts/production_smoke.sh
set -euo pipefail

BASE="${MYWAVE_BASE_URL:-https://mywavewake.ru}"
BASE="${BASE%/}"
DATE="${SMOKE_SLOT_DATE:-$(date +%F)}"
FAIL=0

_check() {
  local name="$1"
  local url="$2"
  local expect="${3:-200}"
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 "$url" || echo "000")"
  if [[ "$code" == "$expect" ]] || [[ "$expect" == *"$code"* ]]; then
    echo "OK   $name  $code  $url"
  else
    echo "FAIL $name  $code (expected $expect)  $url"
    FAIL=1
  fi
}

echo "=== MyWave production smoke ==="
echo "base=$BASE date=$DATE"
echo

_check "home" "$BASE/"
_check "blog" "$BASE/blog"
_check "health" "$BASE/health" "200"
_check "health_live" "$BASE/health/live" "200"
_check "node_chat" "$BASE/node-chat/health" "200"
_check "static_review" "$BASE/static/images/students/Elya_Vesnina.jpg" "200"
_check "slots" "$BASE/api/calendar/slots/${DATE}?service=boat" "200"

echo
echo "=== health body ==="
curl -sS --max-time 15 "$BASE/health" | head -c 500
echo
echo

if [[ "$FAIL" -ne 0 ]]; then
  echo "SMOKE FAILED"
  exit 1
fi
echo "SMOKE OK"
