#!/usr/bin/env bash
# Staging close-out: S8 + S5 + S9. Prod services NOT touched.
set -euo pipefail

STAGING_ROOT="${STAGING_ROOT:-/var/www/mywave-staging}"
cd "$STAGING_ROOT"
source venv/bin/activate
export STAGING_BASE_URL="${STAGING_BASE_URL:-http://127.0.0.1:5002}"
export SECRET_KEY="$(grep -E '^SECRET_KEY=' .env | cut -d= -f2-)"
export S8_DATE="${S8_DATE:-2026-06-12}"
export S5_DATE_GYM_BOAT="${S5_DATE_GYM_BOAT:-2026-06-13}"
export S5_DATE_BOAT_GYM="${S5_DATE_BOAT_GYM:-2026-06-20}"
export STAGING_API_SLEEP="${STAGING_API_SLEEP:-2.5}"

OUT="/tmp/staging_closeout_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT"

echo "=== health ==="
curl -fsS "$STAGING_BASE_URL/health" | python3 -m json.tool | tee "$OUT/health.json"

echo "=== S8 calendar dump ==="
python3 automation/staging/s8_calendar_dump.py | tee "$OUT/s8_calendar.json"

echo "=== S5 travel buffer ==="
python3 automation/staging/s5_seed_schedule.py | tee -a "$OUT/s5_buffer.log"
python3 automation/staging/s5_travel_buffer.py | tee -a "$OUT/s5_buffer.log"

echo "=== S9 orphan check ==="
python3 automation/staging/s9_orphan_check.py | tee "$OUT/s9_orphan.log"

echo "=== done ==="
echo "artifacts: $OUT"
ls -la "$OUT"
