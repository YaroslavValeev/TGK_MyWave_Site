#!/usr/bin/env bash
# Quick production frontend verification (remote). Does NOT replace device QA.
# Usage: bash scripts/verify_production_frontend.sh
set -euo pipefail

BASE="${MYWAVE_BASE_URL:-https://mywavewake.ru}"
BASE="${BASE%/}"
FAIL=0

_ok() { echo "OK   $1"; }
_fail() { echo "FAIL $1"; FAIL=1; }

echo "=== MyWave production frontend verify ==="
echo "base=$BASE date=$(date +%F)"
echo

_code() { curl -sS -o /dev/null -w '%{http_code}' --max-time 20 "$1" 2>/dev/null || echo "000"; }

for path in "/" "/blog" "/projects/checklist-org"; do
  c="$(_code "$BASE$path")"
  [[ "$c" == "200" ]] && _ok "$path $c" || _fail "$path $c (expected 200)"
done

# mobile-home in HTML (same flags as qa_mobile_precheck)
_home="$(curl -sS --compressed -L --max-time 25 "$BASE/" 2>/dev/null || true)"
if grep -Fq 'mobile-home.css?v=3' <<<"$_home" 2>/dev/null || echo "$_home" | grep -Fq 'mobile-home.css?v=3'; then
  _ok "home HTML mobile-home?v=3"
elif echo "$_home" | grep -Fq 'mobile-home.css'; then
  _fail "home HTML mobile-home present but not v=3"
else
  _fail "home HTML mobile-home missing"
fi

# student photos (real photos ~100-400KB, not sketch ~319KB)
len="$(curl -sSI "$BASE/static/images/students/Elya_Vesnina.jpg" 2>/dev/null | awk -F': ' 'tolower($1)=="content-length"{gsub(/\r/,"",$2); print $2}')"
if [[ -n "$len" ]] && [[ "$len" -lt 200000 ]] && [[ "$len" -gt 50000 ]]; then
  _ok "review photo Elya Content-Length=$len"
elif [[ -n "$len" ]]; then
  _fail "review photo Elya Content-Length=$len (expect ~50k-200k, not 319k sketch)"
else
  _fail "review photo Elya no Content-Length"
fi

# checklist
c="$(_code "$BASE/static/images/Project/Cards/checklist/app/app_event_information.webp")"
[[ "$c" == "200" ]] && _ok "checklist webp $c" || _fail "checklist webp $c"

if curl -sS --compressed -L --max-time 25 "$BASE/projects/checklist-org" 2>/dev/null | grep -Fq 'checklist.js?v=cardbg14'; then
  _ok "checklist page cardbg14"
else
  _fail "checklist page cardbg14 (git pull + restart?)"
fi

echo
if [[ "$FAIL" -eq 0 ]]; then
  echo "FRONTEND VERIFY OK — proceed with manual device QA"
  exit 0
fi
echo "FRONTEND VERIFY FAILED — fix before device QA"
exit 1
