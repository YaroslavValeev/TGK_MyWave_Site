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

# Same as manual: curl | grep (use --compressed: nginx may send gzip to script curl)
_curl_home() { curl -sS --compressed -L --max-time 25 "$BASE/" 2>/dev/null; }

if _curl_home | grep -Fq 'mobile-home.css'; then
  echo "OK   html_links_mobile_home_css"
  if _curl_home | grep -Fq 'mobile-home.css?v=3'; then
    echo "OK   html_mobile_home_version  v=3"
  elif _curl_home | grep -Fq 'mobile-home.css?v=2'; then
    echo "FAIL html_mobile_home_version  prod still v=2 — run: sudo systemctl restart mywave-site"
    FAIL=1
  else
    echo "WARN html_mobile_home_version  mobile-home present but ?v= not 3 (check manually)"
    echo "     run: curl -sS $BASE/ | grep -F mobile-home"
  fi
else
  echo "FAIL html_links_mobile_home_css  (mobile-home.css not in home HTML)"
  echo "     manual check: curl -sS $BASE/ | grep mobile-home"
  echo "     if manual OK but script FAIL: git pull (script fix) or nginx gzip — use --compressed"
  FAIL=1
fi

PRECHECK_FAIL=$FAIL

echo
if [[ -f scripts/production_smoke.sh ]]; then
  echo "=== production_smoke.sh ==="
  MYWAVE_BASE_URL="$BASE" bash scripts/production_smoke.sh || true
  echo "(smoke runs even if HTML precheck failed — compare both outputs)"
fi

echo
if [[ "$PRECHECK_FAIL" -ne 0 ]]; then
  echo "PRECHECK FAILED — fix HTML/version before device QA"
  exit 1
fi
echo "PRECHECK OK — proceed with manual device QA (A1/A2/I1/T1)"
