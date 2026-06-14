#!/usr/bin/env bash
# Events-3 staging QA — run ON staging host or with STAGING_BASE_URL reachable.
#
# On VPS (mywave-staging.service binds 127.0.0.1:5002):
#   export STAGING_BASE_URL="http://127.0.0.1:5002"
#   bash scripts/staging_events_qa.sh
#
# External URL (requires nginx + DNS for staging.mywavewake.ru):
#   export STAGING_BASE_URL="https://staging.mywavewake.ru"
#   bash scripts/staging_events_qa.sh
set -euo pipefail

BASE="${STAGING_BASE_URL:-http://127.0.0.1:5002}"
PASS=0
FAIL=0
PARTIAL=0

ok() { echo "[PASS] $*"; PASS=$((PASS + 1)); }
bad() { echo "[FAIL] $*"; FAIL=$((FAIL + 1)); }
warn() { echo "[PARTIAL] $*"; PARTIAL=$((PARTIAL + 1)); }

# HTTP status only; avoid "000000" when curl fails ( -w already prints 000 )
code() {
  local out rc=0
  out=$(curl -sS -o /dev/null -w "%{http_code}" "$1" 2>/dev/null) || rc=$?
  if [[ $rc -ne 0 ]]; then
    echo "000"
  else
    echo "$out"
  fi
}

code_expect() {
  code "$1"
}

echo "=== Events-3 Staging QA ==="
echo "BASE=$BASE"
echo "date=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

HOME_CODE=$(code "$BASE/")
if [[ "$HOME_CODE" == "200" ]]; then ok "home $HOME_CODE"; else bad "home $HOME_CODE (DNS/connectivity? use 127.0.0.1:5002 on VPS)"; fi

EVENTS_CODE=$(code "$BASE/events")
if [[ "$EVENTS_CODE" == "200" ]]; then ok "/events $EVENTS_CODE"; else bad "/events $EVENTS_CODE"; fi

# /competitions redirect (flags ON expected 302)
COMP_HEADERS=$(curl -fsSI "$BASE/competitions" 2>/dev/null || true)
if echo "$COMP_HEADERS" | grep -qi "^HTTP/.* 302"; then
  if echo "$COMP_HEADERS" | grep -qi "type=competition"; then
    ok "/competitions 302 → type=competition"
  else
    warn "/competitions 302 but Location missing type=competition"
  fi
elif echo "$COMP_HEADERS" | grep -qi "^HTTP/.* 404"; then
  warn "/competitions 404 (flags OFF or not deployed?)"
else
  bad "/competitions unexpected: $(echo "$COMP_HEADERS" | head -1)"
fi

# Detail unknown slug → 404 when flags ON
DETAIL_CODE=$(code_expect "$BASE/events/unknown-slug-00000000")
if [[ "$DETAIL_CODE" == "404" ]]; then ok "unknown detail slug 404"; else warn "unknown detail slug $DETAIL_CODE"; fi

# Public HTML safety on /events (temp file — reliable grep on large HTML)
EVENTS_TMP=$(mktemp)
trap 'rm -f "$EVENTS_TMP"' EXIT
if curl -fsS "$BASE/events" -o "$EVENTS_TMP" 2>/dev/null && [[ -s "$EVENTS_TMP" ]]; then
  if grep -qiE 'source_url|raw_content|Traceback' "$EVENTS_TMP"; then
    bad "/events HTML contains forbidden tokens"
  else
    ok "/events no obvious raw leak in HTML"
  fi
  if grep -qF 'mywavewake.ru' "$EVENTS_TMP" || grep -qF 'mywavewake' "$EVENTS_TMP"; then
    ok "mywavewake domain referenced in page"
  elif grep -qF 'rel="canonical"' "$EVENTS_TMP"; then
    ok "canonical link present"
  else
    warn "mywavewake not found in /events HTML (check canonical when flags ON)"
  fi
  if grep -qF 'events-section' "$EVENTS_TMP" || grep -qF 'event-card' "$EVENTS_TMP" || grep -qF 'events-filters' "$EVENTS_TMP"; then
    ok "events markup present (dynamic or YAML cards)"
  else
    warn "no event-card/filters markup"
  fi
  if grep -qF 'application/ld+json' "$EVENTS_TMP"; then
    ok "JSON-LD script on /events"
  else
    warn "JSON-LD script missing on /events"
  fi
else
  warn "/events HTML not fetched (skipped markup/SEO checks)"
fi

# Sitemap
SITEMAP=$(curl -fsS "$BASE/sitemap.xml" 2>/dev/null || true)
if [[ -n "$SITEMAP" ]]; then
  ok "sitemap.xml reachable"
  if echo "$SITEMAP" | grep -q "/events"; then
    ok "sitemap contains /events"
  else
    warn "sitemap missing /events (flags OFF?)"
  fi
else
  bad "sitemap.xml unreachable"
fi

echo ""
echo "=== Summary ==="
echo "PASS=$PASS FAIL=$FAIL PARTIAL=$PARTIAL"
if [[ "$FAIL" -gt 0 ]]; then exit 1; fi
exit 0
