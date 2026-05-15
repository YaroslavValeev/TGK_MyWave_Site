#!/usr/bin/env bash
# Phase 1 automated pre-check (remote) — does NOT replace real device Mobile QA.
# Usage: MYWAVE_BASE_URL=https://mywavewake.ru bash scripts/qa_mobile_precheck.sh
set -euo pipefail

BASE="${MYWAVE_BASE_URL:-https://mywavewake.ru}"
BASE="${BASE%/}"
FAIL=0
CURL_UA="${MYWAVE_PRECHECK_UA:-Mozilla/5.0 (compatible; MyWave-QA-Precheck/1.0)}"

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

# Fetch home HTML once; retry without compression if body looks empty or not HTML.
_fetch_home_html() {
  local tmp err code
  tmp="$(mktemp)"
  err="$(mktemp)"
  code="$(
    curl -sS --compressed -L --max-time 25 \
      -A "$CURL_UA" -o "$tmp" -w '%{http_code}' "$BASE/" 2>"$err" || echo "000"
  )"
  if [[ "$code" != "200" ]]; then
    echo "WARN curl_home_compressed  http=$code  err=$(tr '\n' ' ' <"$err" | head -c 200)" >&2
    rm -f "$tmp" "$err"
    tmp="$(mktemp)"
    err="$(mktemp)"
    code="$(
      curl -sS -L --max-time 25 -H 'Accept-Encoding: identity' \
        -A "$CURL_UA" -o "$tmp" -w '%{http_code}' "$BASE/" 2>"$err" || echo "000"
    )"
  fi
  if [[ ! -s "$tmp" ]] || [[ "$code" != "200" ]]; then
    echo "WARN curl_home  empty_or_bad  http=$code  bytes=$(wc -c <"$tmp" 2>/dev/null || echo 0)" >&2
    cat "$tmp" 2>/dev/null || true
    rm -f "$tmp" "$err"
    return 1
  fi
  # Gzip without decompression → binary; grep would fail
  if ! head -c 256 "$tmp" | grep -qE '<(html|!DOCTYPE)'; then
    echo "WARN curl_home  not_html_like  retry_identity" >&2
    rm -f "$tmp"
    tmp="$(mktemp)"
    code="$(
      curl -sS -L --max-time 25 -H 'Accept-Encoding: identity' \
        -A "$CURL_UA" -o "$tmp" -w '%{http_code}' "$BASE/" 2>/dev/null || echo "000"
    )"
    if [[ "$code" != "200" ]] || [[ ! -s "$tmp" ]]; then
      rm -f "$tmp" "$err"
      return 1
    fi
  fi
  cat "$tmp"
  rm -f "$tmp" "$err"
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

HOME_HTML=""
if ! HOME_HTML="$(_fetch_home_html)"; then
  echo "FAIL html_fetch_home  (could not download home HTML — check curl/DNS/TLS)"
  echo "     manual: curl -sS --compressed -L $BASE/ | head -20"
  FAIL=1
else
  html_bytes="${#HOME_HTML}"
  echo "OK   html_fetch_home  bytes=$html_bytes"

  if grep -Fq 'mobile-home.css' <<<"$HOME_HTML"; then
    echo "OK   html_links_mobile_home_css"
    if grep -Fq 'mobile-home.css?v=3' <<<"$HOME_HTML"; then
      echo "OK   html_mobile_home_version  v=3"
    elif grep -Fq 'mobile-home.css?v=2' <<<"$HOME_HTML"; then
      echo "FAIL html_mobile_home_version  prod still v=2 — run: sudo systemctl restart mywave-site"
      FAIL=1
    else
      echo "WARN html_mobile_home_version  mobile-home present but ?v= not 3 (check manually)"
      echo "     run: curl -sS --compressed -L $BASE/ | grep -F mobile-home"
    fi
  else
    echo "FAIL html_links_mobile_home_css  (mobile-home.css not in home HTML)"
    echo "     static file OK but HTML missing link → usually old Gunicorn templates:"
    echo "       cd /var/www/mywave && git pull --ff-only origin main"
    echo "       grep mobile-home templates/base.html"
    echo "       sudo systemctl restart mywave-site"
    echo "     manual: curl -sS --compressed -L $BASE/ | grep -F mobile-home"
    FAIL=1
  fi
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
