#!/usr/bin/env bash
# Staging close-out: S8 + S5 + S9. Prod services NOT touched.
set -euo pipefail

STAGING_ROOT="${STAGING_ROOT:-/var/www/mywave-staging}"
cd "$STAGING_ROOT"
source venv/bin/activate

export STAGING_ROOT
export STAGING_BASE_URL="${STAGING_BASE_URL:-http://127.0.0.1:5002}"
export STAGING_SPREADSHEET_ID="${STAGING_SPREADSHEET_ID:-16Ewm8Npv3bkNH37X-KAm3PWmRedQ1a8xoiO6LPggyBI}"
export SECRET_KEY="$(grep -E '^SECRET_KEY=' .env | tail -1 | cut -d= -f2-)"
export S8_DATE="${S8_DATE:-2026-06-12}"
export S5_DATE_GYM_BOAT="${S5_DATE_GYM_BOAT:-2026-06-13}"
export S5_DATE_BOAT_GYM="${S5_DATE_BOAT_GYM:-2026-06-20}"
export STAGING_API_SLEEP="${STAGING_API_SLEEP:-2.5}"

OUT="/tmp/staging_closeout_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT"

echo "=== staging context ==="
echo "STAGING_ROOT=$STAGING_ROOT"
echo "STAGING_SPREADSHEET_ID=$STAGING_SPREADSHEET_ID"
sudo -u www-data git -C "$STAGING_ROOT" rev-parse HEAD | tee "$OUT/staging_head.txt"

if grep -q 'self.session.get' "$STAGING_ROOT/automation/staging/_client.py" 2>/dev/null; then
  echo "FATAL: stale automation/staging/_client.py (requests). Run:" >&2
  echo "  cd $STAGING_ROOT && sudo -u www-data git fetch origin main && sudo -u www-data git reset --hard origin/main" >&2
  exit 1
fi
if ! grep -q 'def _curl' "$STAGING_ROOT/automation/staging/_client.py" 2>/dev/null; then
  echo "FATAL: missing curl client in automation/staging/_client.py — git pull required" >&2
  exit 1
fi
if ! grep -q '_staging_env' "$STAGING_ROOT/automation/staging/s9_orphan_check.py" 2>/dev/null; then
  echo "FATAL: stale s9_orphan_check.py — git pull required (staging Sheet guard missing)" >&2
  exit 1
fi

echo "=== health ==="
curl -fsS "$STAGING_BASE_URL/health" | python3 -m json.tool | tee "$OUT/health.json"

echo "=== S8 calendar dump ==="
python3 automation/staging/s8_calendar_dump.py 2>"$OUT/s8_stderr.log" | tee "$OUT/s8_calendar.json"

echo "=== S5 travel buffer ==="
python3 automation/staging/s5_seed_schedule.py 2>>"$OUT/s5_buffer.log" | tee -a "$OUT/s5_buffer.log"
python3 automation/staging/s5_travel_buffer.py 2>>"$OUT/s5_buffer.log" | tee -a "$OUT/s5_buffer.log"

echo "=== S9 orphan check ==="
python3 automation/staging/s9_orphan_check.py 2>>"$OUT/s9_orphan.log" | tee -a "$OUT/s9_orphan.log"

echo "=== done ==="
echo "artifacts: $OUT"
ls -la "$OUT"
