#!/usr/bin/env bash
# Phase 1 automated pre-check (remote) — does NOT replace real device Mobile QA.
# Usage: MYWAVE_BASE_URL=https://mywavewake.ru bash scripts/qa_mobile_precheck.sh
set -euo pipefail

BASE="${MYWAVE_BASE_URL:-https://mywavewake.ru}"
BASE="${BASE%/}"
FAIL=0

_check() {
  local name="$1" url="$2" expect="${3:-200}"
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 "$url" || echo "000")"
  if [[ "$code" == "$expect" ]]; then
    echo "OK   $name  $code  $url"
  else
    echo "FAIL $name  $code (expected $expect)  $url"
    FAIL=1
  fi
}

echo "=== Mobile QA automated pre-check (remote) ==="
echo "base=$BASE date=$(date +%F)"
echo "NOTE: device UX (hero, swipe, safe-area) still requires manual QA."
echo

_check "home" "$BASE/"
_check "blog" "$BASE/blog"
_check "checklist" "$BASE/projects/checklist-org"
_check "mobile_home_css" "$BASE/static/css/mobile-home.css?v=3"
_check "checklist_css" "$BASE/static/css/checklist.css"
_check "static_review" "$BASE/static/images/students/Elya_Vesnina.jpg"

html="$(curl -sS --max-time 20 "$BASE/" || true)"
if echo "$html" | grep -q 'mobile-home.css'; then
  echo "OK   html_links_mobile_home_css"
else
  echo "FAIL html_links_mobile_home_css  (mobile-home.css not found in home HTML)"
  FAIL=1
fi

echo
if [[ -f scripts/production_smoke.sh ]]; then
  echo "=== production_smoke.sh ==="
  MYWAVE_BASE_URL="$BASE" bash scripts/production_smoke.sh || FAIL=1
fi

echo
if [[ "$FAIL" -ne 0 ]]; then
  echo "PRECHECK FAILED — fix before device QA"
  exit 1
fi
echo "PRECHECK OK — proceed with manual device QA (A1/A2/I1/T1)"
