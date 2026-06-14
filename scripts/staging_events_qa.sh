#!/usr/bin/env bash
# Events-3 staging QA — run ON staging host or with STAGING_BASE_URL reachable.
# Usage:
#   export STAGING_BASE_URL="https://staging.mywavewake.ru"
#   bash scripts/staging_events_qa.sh
set -euo pipefail

BASE="${STAGING_BASE_URL:-https://staging.mywavewake.ru}"
PASS=0
FAIL=0
PARTIAL=0

ok() { echo "[PASS] $*"; PASS=$((PASS + 1)); }
bad() { echo "[FAIL] $*"; FAIL=$((FAIL + 1)); }
warn() { echo "[PARTIAL] $*"; PARTIAL=$((PARTIAL + 1)); }

code() {
  curl -sS -o /dev/null -w "%{http_code}" "$1" 2>/dev/null || echo "000"
}

code_expect() {
  # Use curl without -f so 404/503 are readable ( -f would append 000 via || branch)
  curl -sS -o /dev/null -w "%{http_code}" "$1" 2>/dev/null || echo "000"
}

echo "=== Events-3 Staging QA ==="
echo "BASE=$BASE"
echo "date=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

HOME_CODE=$(code "$BASE/")
if [[ "$HOME_CODE" == "200" ]]; then ok "home $HOME_CODE"; else bad "home $HOME_CODE (DNS/connectivity?)"; fi

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

# Public HTML safety on /events
EVENTS_HTML=$(curl -fsS "$BASE/events" 2>/dev/null || true)
if [[ -n "$EVENTS_HTML" ]]; then
  if echo "$EVENTS_HTML" | grep -qi "source_url\|raw_content\|Traceback"; then
    bad "/events HTML contains forbidden tokens"
  else
    ok "/events no obvious raw leak in HTML"
  fi
  if echo "$EVENTS_HTML" | grep -q "mywavewake.ru"; then
    ok "mywavewake.ru referenced in page"
  elif echo "$EVENTS_HTML" | grep -q 'rel="canonical"'; then
    ok "canonical link present"
  else
    warn "mywavewake.ru not found in /events HTML (check canonical when flags ON)"
  fi
  if echo "$EVENTS_HTML" | grep -qE 'events-filters|event-card|events-section'; then
    ok "events markup present (dynamic or YAML cards)"
  else
    warn "no event-card/filters markup"
  fi
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

# JSON-LD on /events
  if echo "$EVENTS_HTML" | grep -qE 'application/ld\+json|application/ld+json'; then
  ok "JSON-LD script on /events"
else
  warn "JSON-LD script missing on /events"
fi

echo ""
echo "=== Summary ==="
echo "PASS=$PASS FAIL=$FAIL PARTIAL=$PARTIAL"
if [[ "$FAIL" -gt 0 ]]; then exit 1; fi
exit 0
