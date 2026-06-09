#!/usr/bin/env bash
# Production Phase 2 — read-only pre-flight (no .env change, no restart, no flags).
# Uses per-invocation safe.directory (no git config --global).
set -euo pipefail

PROD_ROOT="${PROD_ROOT:-/var/www/mywave}"
PROD_URL="${PROD_URL:-https://mywavewake.ru/health}"
ROLLOUT_BASELINE="${ROLLOUT_BASELINE:-27f2d8869ddb269f09e081aa7d10694fb65ee844}"
STAGING_SHEET="16Ewm8Npv3bkNH37X-KAm3PWmRedQ1a8xoiO6LPggyBI"
STAGING_CAL="e4ab0adc25a259eebdf83a506073dd5874dee79890b038f924f164703d187dec"
EXPECTED_PROD_SHEET_TAIL="${EXPECTED_PROD_SHEET_TAIL:-VMOrCgic0}"

GIT=(git -c "safe.directory=${PROD_ROOT}")

failures=0
pass() { echo "PASS: $*"; }
fail() { echo "FAIL: $*"; failures=$((failures + 1)); }
warn() { echo "WARN: $*"; }

echo "=== Production Phase 2 read-only pre-flight ==="
echo "root=${PROD_ROOT}"
echo "ts=$(date -Iseconds 2>/dev/null || date)"

if [[ ! -d "${PROD_ROOT}" ]]; then
  fail "prod root missing: ${PROD_ROOT}"
  exit 1
fi

# --- 1–3. Git HEAD (www-data + safe.directory) ---
echo ""
echo "=== 1. Production HEAD (git -c safe.directory) ==="
if [[ -d "${PROD_ROOT}/.git" ]]; then
  sudo -u www-data "${GIT[@]}" -C "${PROD_ROOT}" fetch origin main 2>&1 || warn "git fetch failed (network?)"
  HEAD="$({ sudo -u www-data "${GIT[@]}" -C "${PROD_ROOT}" rev-parse HEAD; } 2>/dev/null || true)"
  ONELINE="$({ sudo -u www-data "${GIT[@]}" -C "${PROD_ROOT}" log -1 --oneline; } 2>/dev/null || true)"
  ORIGIN="$({ sudo -u www-data "${GIT[@]}" -C "${PROD_ROOT}" rev-parse origin/main; } 2>/dev/null || true)"
  echo "HEAD=${HEAD:-UNKNOWN}"
  echo "log -1: ${ONELINE:-UNKNOWN}"
  echo "origin/main=${ORIGIN:-UNKNOWN}"
  if [[ -n "${HEAD}" ]] && sudo -u www-data "${GIT[@]}" -C "${PROD_ROOT}" merge-base --is-ancestor "${ROLLOUT_BASELINE}" HEAD 2>/dev/null; then
    pass "HEAD >= rollout baseline ${ROLLOUT_BASELINE:0:8}"
  elif [[ -n "${HEAD}" ]]; then
    fail "HEAD < rollout baseline ${ROLLOUT_BASELINE:0:8} (deploy main before Step 1)"
  else
    fail "could not read HEAD (check ownership / safe.directory)"
  fi
else
  fail "no .git in ${PROD_ROOT}"
fi

# --- 4. Effective .env keys (last wins) + duplicate report ---
echo ""
echo "=== 2. Effective SPREADSHEET_ID / GOOGLE_CALENDAR_ID (last wins) ==="
ENV_FILE="${PROD_ROOT}/.env"
if [[ ! -f "${ENV_FILE}" ]]; then
  fail ".env not found"
else
  python3 <<'PY' "${ENV_FILE}" "${EXPECTED_PROD_SHEET_TAIL}" "${STAGING_SHEET}" "${STAGING_CAL}"
import sys
path, expected_tail, staging_sheet, staging_cal = sys.argv[1:5]
values = {}
dupes = {}
with open(path, encoding="utf-8") as fh:
    for i, raw in enumerate(fh, 1):
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k in ("SPREADSHEET_ID", "GOOGLE_CALENDAR_ID"):
            dupes.setdefault(k, []).append((i, v))
        values[k] = v
for key in ("SPREADSHEET_ID", "GOOGLE_CALENDAR_ID"):
    rows = dupes.get(key, [])
    if len(rows) > 1:
        print(f"WARN: duplicate {key} lines ({len(rows)}):")
        for ln, val in rows:
            print(f"  L{ln} tail={val[-12:] if len(val)>=12 else val}")
    eff = values.get(key, "")
    print(f"effective_{key}={eff}")
    print(f"effective_{key}_tail={eff[-12:] if len(eff)>=12 else eff}")
sid = values.get("SPREADSHEET_ID", "")
cal = values.get("GOOGLE_CALENDAR_ID", "")
if staging_sheet in sid or staging_cal in cal:
    print("FAIL: staging ID in effective prod .env value")
    sys.exit(2)
if expected_tail and not sid.endswith(expected_tail):
    print(f"WARN: SPREADSHEET_ID tail != expected ...{expected_tail}")
else:
    print(f"PASS: effective SPREADSHEET_ID tail matches expected ...{expected_tail}")
print("PASS: no staging Sheet/Calendar in effective .env values")
PY
  rc=$?
  [[ $rc -eq 2 ]] && failures=$((failures + 1))
fi

# --- 5. BOOKING_PHASE2 flags ---
echo ""
echo "=== 3. BOOKING_PHASE2_* flags ==="
if grep -qE '^BOOKING_PHASE2_' "${ENV_FILE}" 2>/dev/null; then
  grep -E '^BOOKING_PHASE2_' "${ENV_FILE}" || true
  if grep -E '^BOOKING_PHASE2_' "${ENV_FILE}" | grep -qvE '=0$'; then
    fail "BOOKING_PHASE2 flag set to non-zero"
  else
    pass "BOOKING_PHASE2_* present but all =0"
  fi
else
  pass "no BOOKING_PHASE2_* in .env"
fi

# --- 6. Backup script ---
echo ""
echo "=== 4. Backup script ==="
BACKUP="${PROD_ROOT}/deploy/scripts/backup_mywave.sh"
if [[ -f "${BACKUP}" ]]; then
  bash -n "${BACKUP}" && pass "backup_mywave.sh syntax OK" || fail "backup_mywave.sh syntax error"
  [[ -x "${BACKUP}" ]] && pass "backup_mywave.sh executable" || warn "backup_mywave.sh not executable (may still run via bash)"
else
  fail "missing ${BACKUP}"
fi

# --- 7. Health ---
echo ""
echo "=== 5. Health ==="
HTTP_CODE="$(curl -fsS --max-time 20 -o /tmp/prod_preflight_health.json -w '%{http_code}' "${PROD_URL}" 2>/dev/null || echo "000")"
echo "HTTP ${HTTP_CODE}"
if [[ "${HTTP_CODE}" == "200" ]]; then
  pass "health HTTP 200"
  python3 -m json.tool < /tmp/prod_preflight_health.json 2>/dev/null | head -40 || cat /tmp/prod_preflight_health.json
  python3 <<'PY' /tmp/prod_preflight_health.json
import json, sys
d = json.load(open(sys.argv[1]))
checks = d.get("checks") or d
db = (checks.get("database") or {}).get("status") or checks.get("database")
g = (checks.get("google") or {}).get("status") or checks.get("google")
st = d.get("status", "")
print(f"status={st} database={db} google={g}")
ok = db in ("ok", "healthy", True) and g in ("ok", "healthy", True)
print("PASS: database+google OK" if ok else "FAIL: database or google not OK")
sys.exit(0 if ok else 1)
PY
  [[ $? -ne 0 ]] && failures=$((failures + 1))
else
  fail "health not HTTP 200"
fi

# --- 8. Service status (read-only) ---
echo ""
echo "=== 6. systemd (read-only) ==="
for u in mywave-site mywave-node.service mywave-telegram-bot.service; do
  st="$(systemctl is-active "${u}" 2>/dev/null || echo unknown)"
  echo "${u}: ${st}"
done

echo ""
if [[ $failures -eq 0 ]]; then
  echo "PREFLIGHT_OK"
  exit 0
fi
echo "PREFLIGHT_FAIL count=${failures}"
exit 1
